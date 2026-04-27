# Análise: plano 100% implementado e riscos da tabela antiga

Verificação se o plano de migração estoque → produto_cliente está totalmente implementado e se a tabela `estoque` (removida) ainda pode gerar problemas em algum processo.

---

## 1. Estado do plano – 100% implementado

| Área | Status |
|------|--------|
| Migrations pc02–pc06 | Aplicadas: extensão produtos_cliente, mapa, produto_cliente_id nas tabelas de itens, backfill, drop da tabela estoque e do mapa. |
| Model Estoque e app/models/estoque.py | Removidos. |
| API /api/v1/estoque | Removida; router retirado do main.py. |
| Models VendaItem, NotaFiscalItem, CupomFiscalItem, OrdemServicoItem | Apenas produto_cliente_id; sem estoque_id. |
| Dashboard, Vendas, Ordens de serviço | Usam apenas ProdutoCliente e produto_cliente_id. |
| Frontend (vendas, OS, estoque) | Carregam de /api/v1/produtos-cliente/; enviam produto_cliente_id. |
| Schemas e serviços | Ajustados para produto_cliente_id; schemas/estoque.py removido. |
| Rascunho NFe ao finalizar venda | Preenche NotaFiscalItem.produto_cliente_id. |
| Lacre na OS | Não usado; fluxo que chamava API de lacres removido. |

Conclusão: o plano está 100% implementado em código e fluxos ativos.

---

## 2. Uso da tabela `estoque` – onde ainda aparece

### 2.1 Código de aplicação (runtime)

- **Nenhum** import de `Estoque` ou `app.models.estoque`.
- **Nenhuma** query ou SQL em app/ que use a tabela `estoque` (SELECT/INSERT/UPDATE/DELETE/JOIN).
- As únicas ocorrências de “estoque” em app/ são:
  - **MovimentacaoEstoque** e tabela **movimentacoes_estoque** (entidade diferente, mantida).
  - **ReservaEstoque** e tabela **reserva_estoque** (entidade diferente, mantida).
  - Nomes de variáveis (ex.: `estoque_stats`), comentários e docstrings.
  - Campo **controla_estoque** em ProdutoCliente/MaterialCategoria (atributo de negócio, não a tabela antiga).

Conclusão: em runtime a tabela `estoque` não é mais usada; não há processo ativo que dependa dela.

### 2.2 Migrations (Alembic)

Referências à tabela `estoque` ou à coluna `estoque_id` existem apenas em migrations, na ordem abaixo:

| Migration | O que faz | Risco? |
|-----------|-----------|--------|
| **b89ab470n3x1** | Altera tabela `estoque` (tenant CA). | Não. Roda quando a tabela ainda existe (antes de pc06). |
| **aa00cc247s6** | `ALTER TABLE estoque DROP COLUMN IF EXISTS processo_id`. | Não. Roda antes de pc06; tabela existe. |
| **ll11nn247c7** | `ALTER TABLE estoque DROP COLUMN IF EXISTS agendamento_id, equipamento_id`. | Não. Idem. |
| **pc03_mapear** | `SELECT ... FROM estoque` e preenche mapa. | Não. Roda antes de pc06; tabela existe. |
| **pc05_backfill** | Remove colunas estoque_id; no **downgrade** recria colunas com FK para `estoque.id`. | Só no downgrade: se pc06 já tiver rodado, a tabela não existe e o downgrade quebra. O plano já considera downgrade não implementado (raise NotImplementedError). |

Ordem de execução: as migrations que tocam em `estoque` rodam **antes** de **pc06** (que faz `DROP TABLE estoque`). Depois de pc06, nenhuma migration do plano atual usa a tabela `estoque`.

Conclusão: não há processo de migração “novo” que espere a tabela `estoque` existir após o upgrade completo.

### 2.3 Frontend e chamadas HTTP

- **Nenhum** template ou JS chama `/api/v1/estoque` ou `/api/v1/estoque/...`.
- Páginas de estoque, vendas e ordem de serviço usam `/api/v1/produtos-cliente/`.

Entradas em logs/audit.log para `/api/v1/estoque` são **históricas** (quando a API ainda existia). Hoje essa rota não está registrada; qualquer chamada direta resultaria em 404.

Conclusão: nenhum fluxo de front atual depende da API ou da tabela antiga.

---

## 3. Riscos de a tabela antiga gerar problema

| Cenário | Risco? | Motivo |
|---------|--------|--------|
| Rodar a aplicação após `alembic upgrade head` | Não | Código não referencia Estoque nem tabela estoque. |
| Abrir vendas, OS, estoque, dashboard | Não | Tudo usa produtos_cliente e produto_cliente_id. |
| Fazer nova migração (upgrade) no futuro | Não | Nenhuma migration atual roda depois de pc06 tocando em estoque. |
| Fazer downgrade de pc05/pc06 | Sim, controlado | Downgrade de pc05 tenta recriar FK para `estoque.id`; se a tabela já foi dropada (pc06), falha. Comportamento documentado (downgrade não suportado). |
| Banco já migrado antes da remoção da API | Não | Mesmo que a tabela ainda exista em algum ambiente antigo, o código novo não a usa; ao rodar pc06 nesse ambiente, a tabela é dropada e o uso passa a ser só produtos_cliente. |

Conclusão: a tabela antiga **não** está em nenhum processo que possa quebrar o funcionamento atual do sistema. O único ponto sensível é o downgrade de migrations (já considerado não suportado).

---

## 4. Ajuste feito nesta análise

- **app/core/scope.py**: Comentário em `get_ca_ids_for_cliente_ids` atualizado de “filtrar Estoque” para “escopo por estabelecimento”, pois o filtro passou a ser por estabelecimento (ProdutoCliente), não mais por Estoque.

---

## 5. Resumo

- **Plano:** 100% implementado (models, APIs, migrations, frontend, schemas, serviços e testes considerados).
- **Tabela `estoque`:** Removida pela migration pc06; não é referenciada por nenhum código de aplicação nem por nenhuma migration que rode depois dela.
- **Risco de funcionamento:** Nenhum processo atual usa a tabela antiga; não há risco de a tabela antiga gerar problema no funcionamento do sistema após o upgrade completo.

Data: 2026-03-03.
