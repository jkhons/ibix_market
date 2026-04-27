# Fluxo de entradas de produtos – Negócio/Estoque (resumo)

Rota: **GET /negocio/estoque** → template `meu_negocio/estoque/index.html`.  
Saldo: **produtos_cliente.quantidade_atual**. Histórico: **movimentacoes_estoque**.

**Entradas de produtos (duas formas):**

1. **Entrada manual** — Na tela de estoque, usuário edita o produto e altera a quantidade atual. Front chama **PATCH /api/v1/produtos-cliente/{id}** com `quantidade_atual`; o saldo é atualizado direto na tabela (hoje não gera movimentação de estoque).

2. **Entrada via NFe** — Usuário vai em Entrada de Notas NFe: importa XML (**POST /api/v1/nfe-entrada/importar**) → nota e itens ficam em **nfe_documentos** e **nfe_itens**; na conciliação vincula cada item a um **produto_cliente**; ao clicar em **Confirmar e lançar** (**POST .../confirmar-lancar**), o sistema cria registros em **movimentacoes_estoque** e atualiza **produtos_cliente.quantidade_atual** com as quantidades da nota.

Resumo: entrada manual = PATCH no produto; entrada NFe = importar XML → vincular itens → confirmar e lançar → movimentacoes_estoque + atualização de quantidade_atual.

---

**Tabelas alimentadas por cada fluxo**

| Fluxo | Tabelas alimentadas |
|-------|---------------------|
| **Entrada manual** | **produtos_cliente** (apenas o campo `quantidade_atual` é atualizado; hoje não grava em `movimentacoes_estoque`) |
| **Entrada via NFe** | **nfe_documentos** (cabeçalho da nota ao importar; `status` ao confirmar); **nfe_itens** (itens do XML ao importar; `produto_cliente_id`, `conciliar_status` ao vincular); **movimentacoes_estoque** (uma linha por item ao confirmar e lançar); **produtos_cliente** (`quantidade_atual`, `valor_custo` e opcionalmente NCM, CFOP etc. ao confirmar e lançar). Na vinculação pode ainda atualizar **produtos_fornecedor** (mapa código fornecedor → produto). |
