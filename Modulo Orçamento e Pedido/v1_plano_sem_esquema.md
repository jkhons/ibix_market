📊 VISÃO GERAL: PEDIDO VS ORÇAMENTO
Diferença Conceitual
Orçamento	Pedido
Proposta comercial temporária	Compromisso de venda confirmado
Não movimenta estoque	Movimenta estoque
Não afeta financeiro	Afeta contas a receber
Tem prazo de validade	Vigência até entrega/pagamento
Pode ser convertido em pedido	Pode gerar nota fiscal
Cliente ainda não decidiu	Cliente já aprovou
Analogia prática: Orçamento é como uma "pré-venda" ou "intenção de compra". Pedido é quando o cliente bate o martelo e confirma .

🔄 FLUXO COMPLETO DE FUNCIONAMENTO























📝 ESTRUTURA DE DADOS (BANCO DE DADOS)
Tabelas Fundamentais
sql
-- 1. TABELA DE ORÇAMENTOS
CREATE TABLE orcamentos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    uuid CHAR(36) UNIQUE,
    
    -- Relacionamentos
    cliente_id INT NOT NULL,
    vendedor_id INT NOT NULL,
    estabelecimento_id INT NOT NULL,
    
    -- Dados do orçamento
    numero_orcamento VARCHAR(20) UNIQUE,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_validade DATE NOT NULL,
    status ENUM('rascunho', 'emitido', 'aprovado', 'rejeitado', 'convertido', 'expirado'),
    
    -- Valores
    subtotal DECIMAL(15,2),
    desconto DECIMAL(15,2),
    acrescimo DECIMAL(15,2),
    total DECIMAL(15,2),
    
    -- Observações
    observacoes TEXT,
    condicoes_pagamento TEXT,
    
    -- Controle
    convertido_em_pedido_id INT NULL,
    data_conversao DATETIME NULL,
    
    INDEX idx_cliente (cliente_id),
    INDEX idx_status (status),
    INDEX idx_validade (data_validade)
);

-- 2. ITENS DO ORÇAMENTO
CREATE TABLE orcamento_itens (
    id INT PRIMARY KEY AUTO_INCREMENT,
    orcamento_id INT NOT NULL,
    
    produto_id INT NOT NULL,
    codigo_produto VARCHAR(50),
    descricao_produto VARCHAR(200),
    quantidade DECIMAL(15,3),
    preco_unitario DECIMAL(15,2),
    desconto_percentual DECIMAL(5,2),
    desconto_valor DECIMAL(15,2),
    total_item DECIMAL(15,2),
    
    observacao_item TEXT,
    
    FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);

-- 3. TABELA DE PEDIDOS
CREATE TABLE pedidos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    uuid CHAR(36) UNIQUE,
    
    -- Origem (pode vir de orçamento ou direto)
    orcamento_id INT NULL,
    
    -- Relacionamentos
    cliente_id INT NOT NULL,
    vendedor_id INT NOT NULL,
    estabelecimento_id INT NOT NULL,
    
    -- Dados do pedido
    numero_pedido VARCHAR(20) UNIQUE,
    data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_prevista_entrega DATE,
    
    status ENUM('rascunho', 'liberado', 'bloqueado', 'em_separacao', 
                'faturado_parcial', 'faturado_total', 'cancelado'),
    
    -- Controle de estoque
    reserva_estoque BOOLEAN DEFAULT FALSE,
    data_reserva DATETIME NULL,
    
    -- Valores (podem diferir do orçamento)
    subtotal DECIMAL(15,2),
    desconto DECIMAL(15,2),
    acrescimo DECIMAL(15,2),
    total DECIMAL(15,2),
    
    -- Observações
    observacoes TEXT,
    
    INDEX idx_cliente (cliente_id),
    INDEX idx_status (status),
    INDEX idx_data (data_pedido),
    
    FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id)
);

-- 4. ITENS DO PEDIDO
CREATE TABLE pedido_itens (
    id INT PRIMARY KEY AUTO_INCREMENT,
    pedido_id INT NOT NULL,
    
    produto_id INT NOT NULL,
    codigo_produto VARCHAR(50),
    descricao_produto VARCHAR(200),
    quantidade DECIMAL(15,3),
    quantidade_faturada DECIMAL(15,3) DEFAULT 0,
    preco_unitario DECIMAL(15,2),
    desconto_percentual DECIMAL(5,2),
    desconto_valor DECIMAL(15,2),
    total_item DECIMAL(15,2),
    
    -- Status do item
    status ENUM('pendente', 'parcial', 'faturado', 'cancelado'),
    
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);

-- 5. FATURAMENTO (ligação pedido ↔ notas fiscais)
CREATE TABLE pedido_faturamento (
    id INT PRIMARY KEY AUTO_INCREMENT,
    pedido_id INT NOT NULL,
    nota_fiscal_id INT NOT NULL,
    data_faturamento DATETIME,
    valor_faturado DECIMAL(15,2),
    
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
    FOREIGN KEY (nota_fiscal_id) REFERENCES notas_fiscais(id)
);

-- 6. HISTÓRICO DE STATUS
CREATE TABLE pedido_historico (
    id INT PRIMARY KEY AUTO_INCREMENT,
    pedido_id INT NOT NULL,
    status_anterior VARCHAR(50),
    status_novo VARCHAR(50),
    usuario_id INT NOT NULL,
    observacao TEXT,
    data_mudanca DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
);
🧠 REGRAS DE NEGÓCIO ESSENCIAIS
1. Validade do Orçamento
php
class OrcamentoRules {
    /**
     * Regra: Orçamento expira automaticamente após X dias
     */
    public function verificarValidade(Orcamento $orcamento): void {
        $diasValidade = 7; // Configurável por cliente/estabelecimento
        
        if ($orcamento->status === 'emitido' && 
            $orcamento->data_criacao->diffInDays(now()) > $diasValidade) {
            $orcamento->status = 'expirado';
            $orcamento->save();
        }
    }
    
    /**
     * Regra: Apenas orçamentos válidos podem ser convertidos
     */
    public function podeConverter(Orcamento $orcamento): bool {
        return in_array($orcamento->status, ['emitido', 'aprovado']) && 
               $orcamento->data_validade->isFuture();
    }
}
2. Reserva de Estoque
php
class EstoqueReserva {
    /**
     * Ao converter orçamento em pedido, pode reservar estoque
     */
    public function reservarEstoque(Pedido $pedido): void {
        foreach ($pedido->itens as $item) {
            $estoque = Estoque::where('produto_id', $item->produto_id)
                              ->where('estabelecimento_id', $pedido->estabelecimento_id)
                              ->first();
            
            if ($estoque->quantidade < $item->quantidade) {
                throw new EstoqueInsuficienteException(
                    "Produto {$item->descricao} sem estoque suficiente"
                );
            }
            
            // Reserva (estoque disponível diminui, mas não baixa fisicamente)
            $estoque->quantidade_reservada += $item->quantidade;
            $estoque->save();
        }
        
        $pedido->reserva_estoque = true;
        $pedido->data_reserva = now();
        $pedido->save();
    }
    
    /**
     * Ao faturar, baixa a reserva e o estoque físico
     */
    public function baixarEstoque(Pedido $pedido, array $itensFaturados): void {
        foreach ($itensFaturados as $itemFaturado) {
            $estoque = Estoque::where('produto_id', $itemFaturado['produto_id'])
                              ->first();
            
            // Reduz reserva e estoque físico
            $estoque->quantidade_reservada -= $itemFaturado['quantidade'];
            $estoque->quantidade -= $itemFaturado['quantidade'];
            $estoque->save();
        }
    }
}
3. Faturamento Parcial
php
/**
 * Permite faturar parte do pedido
 * Ex: Cliente pediu 10 itens, entrega 5 agora e 5 depois
 */
class FaturamentoParcial {
    public function faturarParcial(Pedido $pedido, array $itens): NotaFiscal {
        foreach ($itens as $itemData) {
            $itemPedido = PedidoItem::find($itemData['pedido_item_id']);
            
            if ($itemData['quantidade'] > $itemPedido->quantidade - $itemPedido->quantidade_faturada) {
                throw new QuantidadeExcedenteException(
                    "Quantidade excede o pendente do pedido"
                );
            }
            
            // Atualiza quantidade faturada
            $itemPedido->quantidade_faturada += $itemData['quantidade'];
            $itemPedido->status = $this->calcularStatusItem($itemPedido);
            $itemPedido->save();
        }
        
        // Gera nota fiscal com os itens faturados
        $nf = $this->gerarNotaFiscal($pedido, $itens);
        
        // Atualiza status do pedido
        $pedido->status = $this->calcularStatusPedido($pedido);
        $pedido->save();
        
        return $nf;
    }
    
    private function calcularStatusItem(PedidoItem $item): string {
        if ($item->quantidade_faturada == 0) return 'pendente';
        if ($item->quantidade_faturada < $item->quantidade) return 'parcial';
        return 'faturado';
    }
    
    private function calcularStatusPedido(Pedido $pedido): string {
        $totalItens = $pedido->itens->count();
        $itensFaturados = $pedido->itens->where('status', 'faturado')->count();
        
        if ($itensFaturados == 0) return 'em_separacao';
        if ($itensFaturados < $totalItens) return 'faturado_parcial';
        return 'faturado_total';
    }
}
🎯 FUNCIONALIDADES DO DIA A DIA
1. Criação de Orçamento
javascript
// Exemplo de interface de criação
function CriarOrcamento() {
    const [itens, setItens] = useState([]);
    const [cliente, setCliente] = useState(null);
    
    const adicionarProduto = (produto) => {
        setItens([...itens, {
            produto_id: produto.id,
            codigo: produto.codigo,
            descricao: produto.descricao,
            quantidade: 1,
            preco: produto.preco_venda,
            total: produto.preco_venda
        }]);
    };
    
    const calcularTotal = () => {
        return itens.reduce((acc, item) => acc + item.total, 0);
    };
    
    const salvarOrcamento = async () => {
        const payload = {
            cliente_id: cliente.id,
            itens: itens.map(item => ({
                produto_id: item.produto_id,
                quantidade: item.quantidade,
                preco_unitario: item.preco
            })),
            validade_dias: 7
        };
        
        const response = await api.post('/orcamentos', payload);
        
        // Opções após salvar
        if (response.status === 201) {
            // 1. Imprimir orçamento
            // 2. Enviar por WhatsApp
            // 3. Enviar por email
            // 4. Gerar PDF
        }
    };
    
    return (
        <div>
            <h2>Novo Orçamento</h2>
            <ClienteSelector onSelect={setCliente} />
            <ProdutoSearch onAdd={adicionarProduto} />
            
            <table>
                {itens.map((item, idx) => (
                    <tr key={idx}>
                        <td>{item.descricao}</td>
                        <td>
                            <input 
                                type="number" 
                                value={item.quantidade}
                                onChange={(e) => atualizarQuantidade(idx, e.target.value)}
                            />
                        </td>
                        <td>R$ {item.total.toFixed(2)}</td>
                    </tr>
                ))}
            </table>
            
            <div>Total: R$ {calcularTotal().toFixed(2)}</div>
            
            <button onClick={salvarOrcamento}>Salvar Orçamento</button>
        </div>
    );
}
2. Conversão Orçamento → Pedido
php
<?php
class OrcamentoController {
    
    public function converter(Request $request, $id) {
        DB::beginTransaction();
        
        try {
            $orcamento = Orcamento::findOrFail($id);
            
            // Validar se pode converter
            if (!$orcamento->podeConverter()) {
                return response()->json([
                    'error' => 'Orçamento expirado ou já convertido'
                ], 400);
            }
            
            // Criar pedido a partir do orçamento
            $pedido = new Pedido();
            $pedido->orcamento_id = $orcamento->id;
            $pedido->cliente_id = $orcamento->cliente_id;
            $pedido->vendedor_id = $orcamento->vendedor_id;
            $pedido->estabelecimento_id = $orcamento->estabelecimento_id;
            $pedido->numero_pedido = $this->gerarNumeroPedido();
            $pedido->subtotal = $orcamento->subtotal;
            $pedido->desconto = $orcamento->desconto;
            $pedido->total = $orcamento->total;
            $pedido->status = 'liberado';
            $pedido->save();
            
            // Copiar itens
            foreach ($orcamento->itens as $itemOrcamento) {
                $itemPedido = new PedidoItem();
                $itemPedido->pedido_id = $pedido->id;
                $itemPedido->produto_id = $itemOrcamento->produto_id;
                $itemPedido->quantidade = $itemOrcamento->quantidade;
                $itemPedido->preco_unitario = $itemOrcamento->preco_unitario;
                $itemPedido->total_item = $itemOrcamento->total_item;
                $itemPedido->status = 'pendente';
                $itemPedido->save();
            }
            
            // Opcional: reservar estoque
            if ($request->reservar_estoque) {
                $this->estoqueService->reservarEstoque($pedido);
            }
            
            // Atualizar orçamento
            $orcamento->status = 'convertido';
            $orcamento->convertido_em_pedido_id = $pedido->id;
            $orcamento->data_conversao = now();
            $orcamento->save();
            
            DB::commit();
            
            return response()->json([
                'message' => 'Orçamento convertido com sucesso',
                'pedido' => $pedido
            ]);
            
        } catch (\Exception $e) {
            DB::rollBack();
            throw $e;
        }
    }
}
📋 STATUS E FLUXOS ESPECÍFICOS
Orçamento: Ciclo de Vida
text
RASCUNHO ──► EMITIDO ──┬──► APROVADO ──► CONVERTIDO
         │             │
         └──► CANCELADO └──► REJEITADO
                       └──► EXPIRADO
Pedido: Ciclo de Vida
text
RASCUNHO ──► LIBERADO ──► EM_SEPARACAO ──┬──► FATURADO_PARCIAL ──► FATURADO_TOTAL
         │              │                 │
         └──► BLOQUEADO └──► CANCELADO    └──► (aguardando pagamento)
Regras por Tipo de Negócio
Tipo de Negócio	Comportamento Típico
Varejo (loja física)	Venda direta, raramente usa orçamento 
Móveis e decoração	Orçamento é essencial, cliente pensa antes de decidir
Material de construção	Orçamentos grandes, faturamento parcial comum 
Alimentação	Venda rápida, orçamento raro (exceto para eventos)
Serviços	Orçamento detalhado, pode incluir mão de obra
Atacado	Pedidos com reserva de estoque, faturamento por etapas 
🔌 INTEGRAÇÕES COM OUTROS MÓDULOS
1. Integração com Estoque
Orçamento: NÃO mexe no estoque

Pedido liberado: PODE reservar estoque (opcional)

Pedido faturado: BAIXA no estoque obrigatoriamente

2. Integração com Financeiro
Orçamento: NÃO gera contas a receber

Pedido: PODE gerar contas (se configurado)

Faturamento: GERA contas a receber definitivas

3. Integração com Fiscal
Orçamento: NÃO emite nota

Pedido: PODE gerar nota (quando faturado)

Nota fiscal: Vincula ao pedido original 

Histórico de propostas por cliente

Acompanhamento de conversão

🎨 EXEMPLO DE INTERFACE - LISTAGEM DE PEDIDOS
text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    PEDIDOS DE VENDA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILTROS:
┌─────────────────────────────────────────────────────────┐
│ Período: [01/01/2026] até [28/02/2026]                  │
│ Status: [Todos ▼] Cliente: [____________]               │
│ [APLICAR] [LIMPAR]                                      │
└─────────────────────────────────────────────────────────┘

LISTAGEM:
┌────┬──────────┬──────────────┬──────────┬──────────────┐
│ #  │ Nº Pedido│ Cliente      │ Total    │ Status       │
├────┼──────────┼──────────────┼──────────┼──────────────┤
│ 1  │ PED-2026 │ João Silva   │ R$ 1.250 │ 🟢 FATURADO   │
│ 2  │ PED-2025 │ Maria Santos │ R$ 3.420 │ 🟡 EM SEPARAÇÃO│
│ 3  │ PED-2024 │ Pedro Lima   │ R$ 890   │ 🔴 BLOQUEADO  │
│ 4  │ PED-2023 │ Ana Oliveira │ R$ 2.150 │ 🟣 PARCIAL    │
└────┴──────────┴──────────────┴──────────┴──────────────┘

Legenda:
🟢 Faturado  🟡 Em separação  🔴 Bloqueado  🟣 Parcial  ⚪ Cancelado




🔄 FLUXO 1: PDV DIRETO (Venda → Faturamento)
text
VENDA NO PDV ──► FATURAMENTO (NF-e) ──► BAIXA ESTOQUE ──► FINANCEIRO
     │                                    │
     └── (sem pedido intermediário)       └── (imediato ou após pagamento)
Quando usar:
Lojas físicas de varejo

Supermercados

Restaurantes

Farmácias

Qualquer negócio com venda imediata e entrega na hora

Exemplo prático:
Cliente no supermercado passa 10 itens no caixa. O sistema:

Registra a venda

Emite NFC-e na hora

Dá baixa no estoque

Registra o pagamento

Fim. Não existe "pedido" separado

📦 FLUXO 2: PDV + PEDIDO (Venda → Pedido → Faturamento)
text
VENDA NO PDV ──► PEDIDO GERADO ──► SEPARAÇÃO ──► FATURAMENTO ──► ENTREGA
                                                      │
                                                      └── (pode ser parcial)
Quando usar:
Lojas de móveis e eletrodomésticos

Material de construção

Atacado/distribuição

Vendas com entrega agendada

Produtos que precisam de separação/embalagem

Exemplo prático:
Cliente compra uma cozinha planejada e 3 eletrodomésticos:

Vendedor registra a venda no PDV

Sistema gera pedido automaticamente

Pedido vai para o estoque/expedição separar os itens

Alguns itens são faturados hoje (os que têm estoque)

Outros serão faturados quando chegarem do fornecedor

Cliente recebe notas fiscais diferentes ao longo do tempo

🧩 MODELO HÍBRIDO (O MAIS COMUM EM SISTEMAS COMPLETOS)
Na prática, sistemas profissionais suportam ambos os fluxos e permitem configurar por tipo de venda, cliente ou produto.















🏢 COMO ISSO SE APLICA AOS SEUS CLIENTES
Considerando a hierarquia do seu sistema, diferentes tipos de cliente vão usar modelos diferentes:

1. Cliente Varejista (Loja de rua)
text
VENDA → FATURAMENTO DIRETO
- Não quer burocracia
- Precisa de agilidade no caixa
- Cliente leva o produto na hora
2. Cliente Atacadista (Distribuidor)
text
VENDA → PEDIDO → SEPARAÇÃO → FATURAMENTO
- Vende por quantidade
- Precisa separar pedido no estoque
- Pode ter entregas agendadas
- Faturamento parcial comum
3. Cliente Misto (Loja de móveis)
text
VENDA → PEDIDO → AGUARDA ESTOQUE → FATURAMENTO PARCIAL
- Vende produtos que podem não estar em estoque
- Precisa gerenciar "vendas futuras"
- Cliente paga entrada e saldo na entrega
📊 EXEMPLO PRÁTICO NO BANCO DE DADOS
Cenário 1: Venda direta sem pedido
sql
-- A venda já é o documento final
INSERT INTO vendas (id, cliente_id, data_venda, total, status) 
VALUES (1001, 123, NOW(), 150.00, 'concluida');

INSERT INTO venda_itens (venda_id, produto_id, quantidade, preco)
VALUES (1001, 50, 2, 75.00);

-- Gera NF na hora
INSERT INTO notas_fiscais (venda_id, numero, data_emissao, chave_acesso)
VALUES (1001, '000001', NOW(), '352006...');

-- Baixa estoque imediata
INSERT INTO movimentacoes_estoque (produto_id, tipo, quantidade, venda_id)
VALUES (50, 'saida_venda', -2, 1001);
Cenário 2: Venda que gera pedido
sql
-- 1. Registra a venda (origem)
INSERT INTO vendas (id, cliente_id, data_venda, total, status) 
VALUES (1002, 456, NOW(), 5000.00, 'aguardando_faturamento');

-- 2. Sistema gera pedido automaticamente
INSERT INTO pedidos (id, venda_id, numero_pedido, cliente_id, status)
VALUES (2001, 1002, 'PED-2026-001', 456, 'liberado');

-- 3. Itens vão para o pedido
INSERT INTO pedido_itens (pedido_id, produto_id, quantidade, preco)
VALUES (2001, 30, 1, 3000.00),
       (2001, 31, 2, 1000.00);

-- 4. Depois, quando separar/faturar:
UPDATE pedido_itens SET status = 'faturado' WHERE id = ?;
INSERT INTO notas_fiscais (pedido_id, valor, data_emissao) VALUES (2001, 3000.00, NOW());

-- 5. Atualiza status do pedido
UPDATE pedidos SET status = 'faturado_parcial' WHERE id = 2001;
⚙️ CONFIGURAÇÃO NO SISTEMA (FLEXIBILIDADE)
Por tipo de produto
json
{
  "produto": "Geladeira Brastemp",
  "config_venda": {
    "tipo_faturamento": "pedido_obrigatorio",
    "motivo": "Produto grande, precisa agendar entrega"
  }
}
Por tipo de cliente
json
{
  "cliente": "Construtora ABC",
  "config_venda": {
    "tipo_faturamento": "pedido_padrao",
    "faturamento_parcial": true,
    "prazo_entrega_dias": 30
  }
}
Por forma de pagamento
json
{
  "pagamento": "cartao_parcelado",
  "config_venda": {
    "tipo_faturamento": "venda_direta",
    "observacao": "Libera produto apenas após aprovação"
  }
}
🎯 RECOMENDAÇÃO PARA SEU SISTEMA
Arquitetura Flexível
php
<?php
class VendaProcessor {
    
    public function processarVenda(VendaRequest $request) {
        // 1. Criar a venda (sempre existe)
        $venda = $this->criarVenda($request);
        
        // 2. Decidir fluxo baseado em regras
        $fluxo = $this->determinarFluxo($venda);
        
        if ($fluxo === 'direto') {
            // Venda direto para faturamento
            return $this->faturarDireto($venda);
            
        } else if ($fluxo === 'pedido') {
            // Gera pedido intermediário
            $pedido = $this->criarPedido($venda);
            return $this->encaminharParaSeparacao($pedido);
            
        } else if ($fluxo === 'orcamento') {
            // Venda é na verdade um orçamento
            return $this->criarOrcamento($venda);
        }
    }
    
    private function determinarFluxo(Venda $venda): string {
        // Regras de negócio configuráveis
        
        // Se tem itens com entrega futura
        if ($this->temItensSemEstoque($venda)) {
            return 'pedido';
        }
        
        // Se cliente é atacado
        if ($venda->cliente->tipo === 'atacado') {
            return 'pedido';
        }
        
        // Se valor muito alto
        if ($venda->total > 10000) {
            return 'pedido';
        }
        
        // Padrão para varejo
        return 'direto';
    }
}
📈 VANTAGENS DE CADA MODELO
Modelo	Vantagens	Desvantagens
Venda → Faturamento	• Mais rápido
• Menos etapas
• Menos telas	• Não controla separação
• Não gerencia entregas futuras
• Difícil faturamento parcial
Venda → Pedido → Faturamento	• Controle total
• Separação de estoque
• Faturamento parcial
• Rastreabilidade	• Mais burocrático
• Mais telas
• Pode ser lento para varejo
✅ CONCLUSÃO PARA SEU PLANO
O que implementar:
Modelo de dados que suporte ambos os fluxos

Configuração flexível por cliente/produto/pagamento

Transição automática entre venda e pedido quando necessário

Faturamento parcial para pedidos

Relatórios que mostrem o status de cada venda/pedido

Exemplo de configuração na interface:
text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
         CONFIGURAÇÃO DE FLUXO DE VENDAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TIPO DE OPERAÇÃO PADRÃO:
( ) Venda direta (faturamento imediato)
( ) Venda com pedido (separação obrigatória)
(●) Híbrido (decidir por regras)

REGRAS HÍBRIDAS:
[✅] Gerar pedido para produtos sem estoque
[✅] Gerar pedido para clientes atacado
[✅] Gerar pedido para valores acima de R$ [5000,00]
[ ] Gerar pedido para formas de pagamento [parcelado]

FATURAMENTO PARCIAL:
[✅] Permitir faturamento parcial
[ ] Exigir pagamento mínimo de [30]% para liberar parcial

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 RESPOSTA FINAL
Uma venda realizada PODE virar pedido para depois ser faturada, mas não é obrigatório.

O sistema profissional oferece ambos os caminhos e decide com base em:

Tipo de cliente

Tipo de produto

Disponibilidade de estoque

Forma de pagamento

Valor da venda

Configurações do estabelecimento

Isso dá flexibilidade total para atender desde uma padaria (venda direta) até uma construtora (pedidos complexos com faturamento parcial).