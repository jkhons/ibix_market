# Análise: plano de migração estoque → produto_cliente (100%?)

Verificação item a item do plano [migração_estoque_para_produto_cliente_2be6d155.plan.md](.cursor/plans/) contra o estado atual do código.

---

## 1. Módulos/APIs que passam a usar apenas produto_cliente

| Módulo | Plano | Status | Observação |
|--------|--------|--------|------------|
| **API Estoque** | Removida ou proxy para produtos_cliente | ✅ **Feito** | API `app/api/v1/estoque.py` removida; router removido do main.py. |
| **Vendas** | Listar ProdutoCliente; itens só produto_cliente_id; baixa em produtos_cliente | ✅ **Feito** | `vendas.py`: listar produtos via ProdutoCliente, itens só produto_cliente_id, estorno em ProdutoCliente. |
| **Dashboard Negócios** | Estatísticas e joins só ProdutoCliente | ✅ **Feito** | `dashboard_negocios.py`: sem Estoque; bloco estoque e gráficos usam ProdutoCliente. |
| **Notas Fiscais** | NotaFiscalItem só produto_cliente_id | ✅ **Feito** | Model e migrations: produto_cliente_id; estoque_id removido. |
| **Cupons Fiscais** | CupomFiscalItem só produto_cliente_id | ✅ **Feito** | Idem. |
| **Ordem de Serviço** | OrdemServicoItem só produto_cliente_id | ✅ **Feito** | Idem. |

---

## 2. Checklist (Seção 3 do plano)

| Onde | Ação planejada | Status |
|------|----------------|--------|
| app/models/estoque.py | Remover | ✅ Arquivo removido |
| app/models/venda.py | Só produto_cliente_id | ✅ estoque_id e relationship Estoque removidos |
| app/models/nota_fiscal.py | produto_cliente_id; remover estoque_id | ✅ Feito |
| app/models/cupom_fiscal.py | Idem | ✅ Feito |
| app/models/ordem_servico.py | Idem | ✅ Feito |
| app/models/material_categoria.py | Relationship só ProdutoCliente | ✅ "produtos" (Estoque) removido; produtos_cliente mantido |
| app/api/v1/estoque.py | Remover | ✅ Arquivo removido |
| app/api/v1/vendas.py | Só ProdutoCliente e produto_cliente_id | ✅ Feito |
| app/api/v1/dashboard_negocios.py | Só ProdutoCliente | ✅ Feito |
| app/api/v1/ordens_servico.py | OrdemServicoItemResponse produto_cliente_id | ✅ Feito |
| ordem_servico_venda_service.py | VendaItem com produto_cliente_id | ✅ Feito |
| emissao_service.py | produto_cliente_id | ✅ Feito |
| app/schemas/venda.py | Só produto_cliente_id | ✅ Feito |
| app/schemas/nota_fiscal.py, cupom_fiscal.py, ordem_servico.py | produto_cliente_id | ✅ Feito |
| dashboard.html | Sem mudança; backend com ProdutoCliente | ✅ Backend alterado; front usa data.estoque |
| vendas/index.html | produto_cliente_id no payload; exibir produto_cliente_id/código | ✅ Feito |
| ordem_de_servico/index.html | /produtos-cliente; produto_cliente_id; lacre ignorar | ✅ Carrega de produtos-cliente; envia produto_cliente_id; lacre mantido (ignorar) |
| main.py | Remover rota /api/v1/estoque | ✅ Removido |
| Testes | Usar produtos_cliente | ✅ Ajustados |

---

## 3. Migrations (Seção 4)

| Migration | Descrição | Status |
|-----------|-----------|--------|
| **1** | Estender produtos_cliente (categoria, tipo_material, categoria_id, fabricante, fornecedor, data_validade, data_fabricacao, controla_estoque, quantidade_maxima) | ✅ pc02_produtos_cliente_estender_estoque_campos.py |
| **2** | Mapear Estoque → ProdutoCliente; tabela de mapa | ✅ pc03_mapear_estoque_para_produtos_cliente.py |
| **3** | Adicionar produto_cliente_id em notas_fiscais_itens, cupons_fiscais_itens, ordem_servico_itens | ✅ pc04_add_produto_cliente_id_nf_cupom_os.py |
| **4** | Backfill produto_cliente_id e remover coluna estoque_id das 4 tabelas | ✅ pc05_backfill_remove_estoque_id.py |
| **5** | Dropar tabela estoque (e mapa) | ✅ pc06_drop_estoque_and_map.py |

---

## 4. Backend – trocas por componente (Seção 5)

- API Estoque: removida e registro em main.py removido. ✅  
- API Vendas: listagem ProdutoCliente; itens só produto_cliente_id; estorno em ProdutoCliente. ✅  
- Dashboard: bloco estoque e gráficos só ProdutoCliente. ✅  
- Ordens de serviço: resposta e criar/editar com produto_cliente_id. ✅  
- ordem_servico_venda_service: valida e preenche produto_cliente_id. ✅  
- emissao_service: payload com produto_cliente_id. ✅  
- Schemas venda, nota_fiscal, cupom_fiscal, ordem_servico: produto_cliente_id. ✅  
- Models: estoque_id e Estoque removidos; ProdutoCliente com novos campos; MaterialCategoria sem Estoque. ✅  

---

## 5. Frontend (Seção 6)

| Tela | Requisito | Status |
|------|-----------|--------|
| **Dashboard** | Contrato data.estoque; backend com ProdutoCliente | ✅ Sem mudança de contrato; backend preenche com ProdutoCliente. |
| **Vendas** | Carregar produtos via /api/v1/produtos-cliente/; payload produto_cliente_id; exibir produto_cliente_id/código | ✅ Corrigido: produtos carregados via **GET /api/v1/produtos-cliente/** (com cliente_id opcional); payload e exibição com produto_cliente_id. |
| **Ordem de serviço** | /produtos-cliente; produto_cliente_id no item; lacre ignorar | ✅ Carrega de /api/v1/produtos-cliente/; envia produto_cliente_id; lacre mantido (plano: “remover ou ignorar”). |
| **Estoque** | Só produtos-cliente; sem /api/v1/estoque | ✅ Todas as chamadas são para /api/v1/produtos-cliente/. |

---

## 6. Itens não obrigatórios / observações (corrigidos)

- **app/schemas/estoque.py**: ✅ Removido (limpeza pós-migração).
- **Rascunho NFe ao finalizar venda**: ✅ Corrigido: `_criar_rascunho_nfe_ao_finalizar_venda` agora preenche `NotaFiscalItem.produto_cliente_id` ao criar itens a partir da venda.
- **Lacre na OS**: ✅ Corrigido: fluxo que abria modal de lacre (e chamava API lacres-selos) foi removido; itens são sempre adicionados como produto_cliente (Lacre não é usado neste modelo).
- **Comentários em migrations**: Referências a “estoque_id” em comentários e strings das migrations (pc03, pc05) são apenas documentação histórica; não indicam uso de Estoque no app.

---

## 7. Conclusão

- **Implementação em relação ao plano: ~100%.**
- **Obrigatório pelo plano**: concluído (migrations, models, APIs, schemas, frontend vendas/OS/estoque/dashboard, testes, remoção da API e do model Estoque).
- **Lacunas corrigidas (pós-análise)**:
  - Vendas: passou a carregar produtos via **GET /api/v1/produtos-cliente/** (com `cliente_id` opcional do estabelecimento).
  - Removido `app/schemas/estoque.py`.
  - Rascunho NFe ao finalizar venda: itens passam a ter `produto_cliente_id` preenchido.
  - OS: fluxo de lacre removido; itens sempre adicionados como produto (Lacre não usado).

Data da análise: 2026-03-03. Lacunas corrigidas em seguida.
