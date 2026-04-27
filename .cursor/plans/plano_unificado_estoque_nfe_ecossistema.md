---
name: Plano unificado estoque NFe e ecossistema
overview: "Plano da correção da quantidade NFe não importada para o estoque — validações E.1/E.2, bloco fiscal isolado, front conciliar. O ecossistema/marketplace (vitrine, Minha loja, checkout, NF-e comprador, notificação ao CA) está em plano separado: [plano_marketplace.md](.cursor/plans/plano_marketplace.md)."
todos: []
isProject: false
---

# Plano unificado: Correção NFe/estoque (entrada NFe → estoque)

**Parte I** — correção do fluxo "Confirmar e lançar" (entrada NFe → estoque). **Parte II** (ecossistema/marketplace) — ver [plano_marketplace.md](.cursor/plans/plano_marketplace.md).

---

# PARTE I — Correção da quantidade NFe não importada para o estoque

## I.1 Contexto

- **Importação XML:** a quantidade é gravada em `nfe_itens.qcom_xml` e exibida no modal "Vincular ao produto interno".
- **Entrada em estoque:** POST `/api/v1/nfe-entrada/documentos/{nfe_id}/confirmar-lancar` chama `confirmar_e_lancar_estoque`, que cria `movimentacoes_estoque` e atualiza `produtos_cliente.quantidade_atual`.

Se a quantidade não aparece no estoque após "Confirmar e lançar", causas prováveis: exceção no bloco fiscal revertendo toda a transação; produto fora do escopo do estabelecimento.

## I.2 Pontos de falha e ajustes

### Falha 1: Exceção no bloco fiscal reverte tudo

Em [app/services/fiscal/nfe_entrada_service.py](app/services/fiscal/nfe_entrada_service.py), cada item é processado em um único `try/except`: movimento + quantidade + preenchimento fiscal (NCM, CFOP, etc.). Se qualquer linha do bloco fiscal lançar exceção, o `except` anexa em `erros` e no final `db.rollback()` desfaz **toda** a transação — inclusive quantidade e movimento.

**Ajuste A:** Separar em dois blocos por item:
1. **Bloco principal (obrigatório):** criar `MovimentacaoEstoque`, buscar `ProdutoCliente` (com `doc.cliente_id`), atualizar `quantidade_atual`; **ordem:** `db.add(mov)` → `prod.quantidade_atual += quantidade` → `db.flush()`. Qualquer exceção aqui → `erros` e rollback.
2. **Bloco fiscal (opcional):** preencher NCM, CFOP, CEST, etc. no produto. Envolver **só esse trecho** em `try/except`: em caso de exceção, apenas log (sem adicionar a `erros` que dispara rollback). Estoque é operacional; fiscal é complementar.

### Falha 2: Busca do produto sem escopo

**Ajuste B:** Na busca do produto, filtrar por `ProdutoCliente.cliente_id == doc.cliente_id`. Se `prod` for `None`, não criar movimento; adicionar erro explícito e rollback do documento.

### Regra atômica e garantias

**Ajuste C:** Confirmação atômica por documento. Se qualquer item falhar no bloco principal → rollback do documento inteiro.

**E.1 — Todos itens vinculados:** Antes do loop, validar `if any(not c.get("produto_cliente_id") for c in custos): return 0, ["Existem itens não vinculados. Vincule todos os itens antes de confirmar e lançar."]`

**E.2 — Evitar duplo lançamento:** Antes do processamento, checar se já existe `MovimentacaoEstoque` com `nfe_documento_id == nfe_id`; se existir, retornar erro "Documento já lançado no estoque."

**E.3 — Log da quantidade:** Após `prod.quantidade_atual += quantidade`, logar (INFO) algo como: `NFe {doc.id} | Produto {prod.id} | +{quantidade} | Novo saldo {prod.quantidade_atual}`.

## I.3 Front (entrada NFe) — ✅ 100% amparado

- **Erro:** Na tela [app/templates/meu_negocio/entrada_nfe/conciliar.html](app/templates/meu_negocio/entrada_nfe/conciliar.html), em caso de resposta não ok, exibir no alert o `detail` completo da API; se `detail` vier como array: `(Array.isArray(data.detail) ? data.detail.join('; ') : data.detail) || 'Erro ao confirmar.'`. **Implementado:** linhas 290–291 já usam essa lógica.
- **Sucesso:** Alert com `movimentacoes_criadas` e redirecionamento para `/negocio/entrada-nfe`. **Implementado.** Lista de notas ([app/templates/meu_negocio/entrada_nfe/index.html](app/templates/meu_negocio/entrada_nfe/index.html)) já exibe coluna "Itens vinculados" (X / Y), badge de status CONCILIADO e link para conciliação.

## I.4 O que NÃO fazer nesta fase (Parte I)

Custo médio ponderado, lançamento manual, coluna `origem`, integração financeiro — ficam para fase 2.

---

# Ordem de implementação

1. **Correção NFe/estoque:** Em `confirmar_e_lancar_estoque`: validações E.1 (todos vinculados) e E.2 (documento não já lançado); refatorar loop (bloco movimento + quantidade + flush; depois bloco fiscal em try/except); busca produto com `doc.cliente_id`; tratar `prod is None`; log (E.3) e WARNING quando produto não encontrado. **Front:** conciliar.html — alert com `detail` completo (array unido com "; ").
2. **Documentação:** MAPA_DO_SISTEMA: fluxo entrada NFe → estoque (validações, flush, bloco fiscal, atômico).
3. **Testes:** Fluxo importar XML → vincular → Confirmar e lançar (conferir movimentacoes e quantidade_atual; simular dado fiscal inválido e garantir que quantidade persiste).
4. **Ecossistema/marketplace:** Ver [plano_marketplace.md](.cursor/plans/plano_marketplace.md).

---

# Arquivos a alterar (Parte I)

| Área | Arquivos e alteração |
|------|----------------------|
| **NFe/estoque** | [app/services/fiscal/nfe_entrada_service.py](app/services/fiscal/nfe_entrada_service.py): refatorar loop (bloco movimento+quantidade+flush, bloco fiscal isolado), filtrar produto por `doc.cliente_id`, E.1/E.2/E.3, logs. |
| **Front** | [app/templates/meu_negocio/entrada_nfe/conciliar.html](app/templates/meu_negocio/entrada_nfe/conciliar.html): alert com `detail` completo (se array, join "; "). |
| **Parte II (marketplace)** | Ver [plano_marketplace.md](.cursor/plans/plano_marketplace.md). |

---

**Conclusão:** Este plano cobre apenas a correção da quantidade NFe no estoque (entrada NFe → "Confirmar e lançar"). O ecossistema e marketplace estão no plano dedicado [plano_marketplace.md](.cursor/plans/plano_marketplace.md).
