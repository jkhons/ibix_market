# FLUXO FINANCEIRO

## Visão Geral

Este documento detalha o fluxo completo do módulo financeiro no PDV Ibix, incluindo vendas, notas fiscais (NF-e/NFC-e), notas de serviço (NFS-e) e cupons fiscais.

**Modelos:** `app/models/venda.py`, `app/models/nota_fiscal.py`, `app/models/nota_servico.py`, `app/models/cupom_fiscal.py`  
**APIs:** `app/api/v1/vendas.py`, `app/api/v1/notas_fiscais.py`, `app/api/v1/notas_servico.py`, `app/api/v1/cupons_fiscais.py`

---

## Pré-requisitos

- Empresa cadastrada (obrigatório para emissão fiscal) — dados do **emissor** (Cliente = Empresa Fiscal)
- Cliente cadastrado (opcional, pode ser venda avulsa) — quando informado, representa o **destinatário** (Subcliente)
- Ordem de serviço ou certificado (opcional)
- Usuário autenticado com permissão para criar vendas/notas

**Uso fiscal (emissor/destinatário):** Na emissão de notas, o **emissor** é a Empresa Fiscal (Cliente Administrador; dados em `empresa`); o **destinatário** é o Subcliente (`nota_fiscal.cliente_id`, `nota_servico.cliente_id`).

---

## Fluxo Principal: Venda → Documento Fiscal

```mermaid
flowchart TD
    Start([Criar venda]) --> ValidarPermissao{Usuário tem permissão?}
    ValidarPermissao -->|Não| ErroPermissao[Erro: Sem permissão]
    ValidarPermissao -->|Sim| SelecionarOrigem[Selecionar origem]
    
    SelecionarOrigem --> TemOS{Tem ordem de serviço?}
    TemOS -->|Sim| VincularOS[Vincular ordem de serviço]
    TemOS -->|Não| TemCertificado{Tem certificado?}
    
    VincularOS --> ValidarOS{OS válida?}
    ValidarOS -->|Não| ErroOS[Erro: OS inválida]
    ValidarOS -->|Sim| PreencherDados
    TemCertificado -->|Sim| VincularCertificado[Vincular certificado]
    TemCertificado -->|Não| PreencherDados[Preencher dados da venda]
    
    VincularCertificado --> ValidarCertificado{Certificado válido?}
    ValidarCertificado -->|Não| ErroCertificado[Erro: Certificado inválido]
    ValidarCertificado -->|Sim| PreencherDados
    
    PreencherDados --> AdicionarItens[Adicionar itens/produtos]
    AdicionarItens --> CalcularTotal[Calcular total]
    CalcularTotal --> CriarVenda[Criar venda]
    
    CriarVenda --> EmitirDocumento{Emitir documento fiscal?}
    EmitirDocumento -->|Sim| SelecionarTipo{Tipo de documento?}
    EmitirDocumento -->|Não| Sucesso
    
    SelecionarTipo -->|NF-e| EmitirNFe[Emitir Nota Fiscal Eletrônica]
    SelecionarTipo -->|NFC-e| EmitirNFCe[Emitir Cupom Fiscal Eletrônico]
    SelecionarTipo -->|NFS-e| EmitirNFSe[Emitir Nota de Serviço Eletrônica]
    
    EmitirNFe --> ValidarEmpresa{Empresa válida?}
    EmitirNFCe --> ValidarEmpresa
    EmitirNFSe --> ValidarEmpresa
    
    ValidarEmpresa -->|Não| ErroEmpresa[Erro: Empresa não configurada]
    ValidarEmpresa -->|Sim| EmitirDocumento[Emitir documento]
    EmitirDocumento --> VincularDocumento[Vincular documento à venda]
    VincularDocumento --> Sucesso[Venda criada com documento fiscal]
    
    ErroPermissao --> End([Fim])
    ErroOS --> End
    ErroCertificado --> End
    ErroEmpresa --> End
    Sucesso --> End
    
    style Start fill:#e1f5ff
    style Sucesso fill:#e1ffe1
    style ErroPermissao fill:#ffe1e1
    style ErroOS fill:#ffe1e1
    style ErroCertificado fill:#ffe1e1
    style ErroEmpresa fill:#ffe1e1
```

---

## Tipos de Documentos Fiscais

### Nota Fiscal Eletrônica (NF-e)
- **Modelo:** 55
- **Uso:** Vendas de produtos
- **Obrigatório:** Empresa configurada, cliente (opcional)

### Cupom Fiscal Eletrônico (NFC-e)
- **Modelo:** 65
- **Uso:** Vendas no varejo
- **Obrigatório:** Empresa configurada

### Nota de Serviço Eletrônica (NFS-e)
- **Uso:** Prestação de serviços
- **Obrigatório:** Empresa configurada, cliente (opcional)

---

## Campos Obrigatórios

### Venda
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `numero_venda` | String(50) | Número único da venda |
| `data_venda` | DateTime | Data da venda |
| `vendedor_id` | Integer | FK para `usuarios.id` |
| `subtotal` | Decimal(10,2) | Subtotal |
| `total` | Decimal(10,2) | Total |

### Nota Fiscal
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `numero` | String(20) | Número da nota |
| `serie` | String(10) | Série da nota |
| `tipo` | Enum | Tipo: NFe, NFCe |
| `modelo` | String(5) | Modelo: 55 ou 65 |
| `data_emissao` | DateTime | Data de emissão |
| `empresa_id` | Integer | FK para `empresa.id` — **emissor** (Empresa Fiscal) |
| `cliente_id` | Integer | FK para `clientes.id` — **destinatário** (Subcliente) |
| `valor_total` | Decimal(10,2) | Valor total |

---

## Fluxo de Pagamento

```mermaid
flowchart TD
    Start([Venda criada]) --> DefinirPagamento[Definir forma de pagamento]
    DefinirPagamento --> TipoPagamento{Tipo de pagamento?}
    
    TipoPagamento -->|Dinheiro| PagamentoDinheiro[Pagamento em dinheiro]
    TipoPagamento -->|Cartão| PagamentoCartao[Pagamento com cartão]
    TipoPagamento -->|Boleto| PagamentoBoleto[Pagamento via boleto]
    TipoPagamento -->|PIX| PagamentoPIX[Pagamento via PIX]
    
    PagamentoDinheiro --> CalcularTroco[Calcular troco]
    PagamentoCartao --> ProcessarCartao[Processar pagamento]
    PagamentoBoleto --> GerarBoleto[Gerar boleto]
    PagamentoPIX --> GerarPIX[Gerar QR Code PIX]
    
    CalcularTroco --> RegistrarPagamento[Registrar pagamento]
    ProcessarCartao --> RegistrarPagamento
    GerarBoleto --> RegistrarPagamento
    GerarPIX --> RegistrarPagamento
    
    RegistrarPagamento --> AtualizarStatus[Atualizar status da venda]
    AtualizarStatus --> Sucesso[Pagamento registrado]
    
    Sucesso --> End([Fim])
    
    style Start fill:#e1f5ff
    style Sucesso fill:#e1ffe1
```

---

## Relacionamentos

```mermaid
erDiagram
    VENDA }o--o| CLIENTE : pertence_a
    VENDA }o--o| ORDEM_SERVICO : vinculada_a
    VENDA }o--o| CERTIFICADO : vinculada_a
    VENDA }o--o| NOTA_FISCAL : gera
    VENDA }o--o| NOTA_SERVICO : gera
    VENDA }o--o| CUPOM_FISCAL : gera
    
    NOTA_FISCAL }o--|| EMPRESA : emitida_por
    NOTA_FISCAL }o--o| CLIENTE : destinatario
    NOTA_FISCAL ||--o{ NOTA_FISCAL_ITEM : tem_itens
    
    NOTA_SERVICO }o--|| EMPRESA : emitida_por
    NOTA_SERVICO }o--o| CLIENTE : destinatario
    
    style VENDA fill:#e1f5ff
    style NOTA_FISCAL fill:#ffe1e1
    style NOTA_SERVICO fill:#ffe1e1
```

---

## APIs Envolvidas

### Criar Venda
```
POST /api/v1/vendas
Content-Type: application/json

{
  "cliente_id": 1,
  "vendedor_id": 1,
  "subtotal": 1000.00,
  "desconto": 0.00,
  "total": 1000.00,
  "tipo_pagamento": "cartao"
}

Response: 201 Created
```

### Emitir Nota Fiscal
```
POST /api/v1/notas-fiscais
Content-Type: application/json

{
  "venda_id": 1,
  "empresa_id": 1,
  "cliente_id": 1,
  "tipo": "NFe",
  "modelo": "55",
  "itens": [...]
}

Response: 201 Created
```

---

## Regras de Negócio

1. **Empresa Obrigatória:** Documentos fiscais requerem empresa configurada
2. **Cliente Opcional:** Venda pode ser avulsa (sem cliente)
3. **Vinculação:** Venda pode estar vinculada a OS ou certificado
4. **Documento Fiscal:** Venda pode gerar NF-e, NFC-e ou NFS-e
5. **Pagamento:** Venda pode ter múltiplas formas de pagamento

---

## Referências

- [INDICE.md](INDICE.md) - Índice dos fluxos
- [FLUXO_ORDEM_SERVICO.md](FLUXO_ORDEM_SERVICO.md) - Fluxo de ordens de serviço
- [FLUXO_CERTIFICACAO_CALIBRACAO.md](FLUXO_CERTIFICACAO_CALIBRACAO.md) - Certificados e calibração
- MAPA_SISTEMA/MAPA_DO_SISTEMA.md - Estrutura do banco (Parte 2)

---

**Última Atualização:** 2026-02-08 (Terminologia emissor/destinatário: Empresa Fiscal = emissor, Subcliente = destinatário)
