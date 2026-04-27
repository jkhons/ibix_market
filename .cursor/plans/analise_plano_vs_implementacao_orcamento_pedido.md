# Análise analítica: Plano vs Implementação — Módulo Orçamento e Pedido (solumatica_auto)

**Plano:** `replicar_módulo_orçamento_e_pedido_no_solumatica_auto_a6566b2d.plan.md`  
**Implementação:** projeto `solumatica_auto`  
**Data da análise:** 2026-02-28

---

## 1. Metodologia

Cada requisito explícito do plano (seções 1 a 12) foi confrontado com o código em `solumatica_auto`. Itens marcados como **OK** estão implementados e alinhados ao plano; **Pendência** indica gap ou desvio; **Observação** indica detalhe que não invalida o plano.

---

## 2. Resultado por seção do plano

### 2.1 Banco de dados (Alembic)

| Requisito | Status | Verificação |
|-----------|--------|-------------|
| Migration 1.1: tabelas orcamentos, orcamento_itens, pedidos, pedido_itens, pedido_faturamento, pedido_historico, reserva_estoque | **OK** | `sa_or01pd02_add_orcamentos_pedidos.py` cria as 7 tabelas com colunas, FKs, índices e UNIQUE conforme referência. |
| Migration 1.1: coluna `notas_fiscais.pedido_id` (Integer, nullable, FK pedidos.id, ondelete SET NULL) + índice | **OK** | upgrade() adiciona coluna, FK e `ix_notas_fiscais_pedido_id`. |
| Migration 1.1: `down_revision` coerente com o head do Alembic | **OK** | `down_revision = "vv22ww024k2t7"`; head atual é `sa_ww33xx137n3x1`. |
| Migration 1.2: inserir 5 permissões (negocios.orcamento:visualizar, :criar, negocios.pedido:visualizar, :criar, :faturar) | **OK** | `sa_ww33xx137n3x1_seed_permissoes_orcamento_pedido.py` com PERMISSOES_ORCAMENTO_PEDIDO e INSERT condicional (`SELECT 1 FROM permissoes WHERE nome = :n`). |
| Migration 1.2: associar às roles Superadministrador, Administrador, Cliente Administrador | **OK** | ROLES_COM_PERMISSAO e _assign_permissao_to_role com SELECT id FROM roles/permissoes. |
| Migration 1.2: colunas permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at) | **OK** | INSERT usa exatamente essas colunas; model Permissao possui nome, descricao, modulo, acao, ativo; BaseModel fornece created_at/updated_at. |
| Migration 1.2: tabelas permissoes e role_permissoes | **OK** | Seed usa `permissoes` e `role_permissoes`; models conferidos. |
| Migration 1.2: down_revision = revision da 1.1 | **OK** | `down_revision = "sa_or01pd02"`. |

---

### 2.2 Models (SQLAlchemy)

| Requisito | Status | Verificação |
|-----------|--------|-------------|
| Criar app/models/orcamento.py | **OK** | Arquivo existe; imports e BaseModel ajustados. |
| Orcamento: relationship convertido_em_pedido com foreign_keys, remote_side=[Pedido.id], uselist=False, **sem** back_populates | **OK** | orcamento.py: `convertido_em_pedido = relationship("Pedido", foreign_keys=[...], remote_side=[Pedido.id], uselist=False)`. |
| Criar app/models/pedido.py | **OK** | Arquivo existe. |
| Pedido: relationship orcamento com foreign_keys=[orcamento_id], uselist=False, **sem** back_populates | **OK** | pedido.py: `orcamento = relationship("Orcamento", foreign_keys=[orcamento_id], uselist=False)`. |
| __init__.py: importar e reexportar Orcamento, OrcamentoItem, Pedido, PedidoItem, PedidoFaturamento, PedidoHistorico, ReservaEstoque | **OK** | Todos exportados em app/models/__init__.py. |
| __init__.py: ordem — pedido antes de orcamento | **OK** | Comentário e ordem: `from .pedido import ...` depois `from .orcamento import ...`. |
| nota_fiscal.py: coluna pedido_id (Integer, FK pedidos.id, nullable, index) | **OK** | Column com ForeignKey e index. |
| nota_fiscal.py: relationship `pedido = relationship("Pedido", foreign_keys=[pedido_id])` por string, sem importar Pedido | **OK** | Uso de string "Pedido" evita import circular. |

---

### 2.3 Schemas (Pydantic)

| Requisito | Status | Verificação |
|-----------|--------|-------------|
| Criar app/schemas/orcamento.py | **OK** | Arquivo existe com OrcamentoCreate, OrcamentoUpdate, OrcamentoResponse, OrcamentoListResponse, OrcamentoItemCreate/Response, OrcamentoConverterRequest. |
| Criar app/schemas/pedido.py | **OK** | Arquivo existe com PedidoCreate, PedidoUpdate, PedidoResponse, PedidoListResponse, PedidoItemCreate/Response, PedidoFaturarBody/Request. |

---

### 2.4 Services

| Requisito | Status | Verificação |
|-----------|--------|-------------|
| orcamento_service: expirar_orcamentos, validar_para_conversao | **OK** | Funções presentes. |
| pedido_service: reservar_estoque, liberar_reserva, faturar_pedido (NF rascunho + PedidoFaturamento) | **OK** | Funções presentes; faturar_pedido cria NotaFiscal com pedido_id e origem_documento=ORCAMENTO. |
| pedido_service: obter Empresa por Empresa.cliente_id == ped.cliente_id | **OK** | `db.query(Empresa).filter(Empresa.cliente_id == ped.cliente_id).first()`. |
| pdf_orcamento_pedido: import lazy do WeasyPrint dentro da função (ex.: _html_to_pdf) | **OK** | `from weasyprint import HTML` dentro de _html_to_pdf. |
| pdf_orcamento_pedido: capturar ImportError e OSError, relançar RuntimeError com mensagem clara | **OK** | try/except em _html_to_pdf com ImportError e OSError. |

---

### 2.5 APIs (FastAPI)

| Requisito | Status | Verificação |
|-----------|--------|-------------|
| Criar app/api/v1/orcamentos.py (get_db, get_current_user, forbid_cliente_access, get_cliente_scope_dep, ClienteScope) | **OK** | Router com prefix /orcamentos e dependências corretas. |
| Criar app/api/v1/pedidos.py (idem, prefix /pedidos) | **OK** | Router com prefix /pedidos. |
| relatorios.py: GET /conversao-orcamentos (data_inicio, data_fim, cliente_id opcionais) | **OK** | Endpoint existe com Query(None). |
| relatorios: filtro por data_inicio/data_fim com datetime.combine (intervalo inclusivo) | **OK** | `datetime.combine(data_inicio, datetime.min.time())` e `datetime.combine(data_fim, datetime.max.time())`. |
| relatorios: get_cliente_scope_dep e _allowed_ids | **OK** | Uso de scope e filtro por allowed_ids. |
| main.py ROUTER_SPECS: orcamentos e pedidos | **OK** | Entradas para app.api.v1.orcamentos e app.api.v1.pedidos (atributo router). |
| main.py ROUTER_INCLUDE: ("orcamentos", "/api/v1", None) e ("pedidos", "/api/v1", None) | **OK** | Inclusão presente. |

---

### 2.6 Rotas HTML (main.py)

| Requisito | Status | Verificação |
|-----------|--------|-------------|
| GET /negocio/orcamentos (perm. negocios.orcamento:visualizar) | **OK** | Rota existe; check_html_module_permission("negocios") + checagem "negocios.orcamento:visualizar" e Superadministrador. |
| GET /negocio/orcamentos/novo | **OK** | Rota existe; checagem visualizar ou criar + Superadministrador. |
| GET /negocio/orcamentos/{orcamento_id:int}/editar | **OK** | Rota existe; context["orcamento_id"] = orcamento_id. |
| GET /negocio/pedidos (perm. negocios.pedido:visualizar) | **OK** | Rota existe; checagem análoga. |
| GET /negocio/pedidos/novo | **OK** | Rota existe. |
| GET /negocio/pedidos/{pedido_id:int}/editar | **OK** | Rota existe; context["pedido_id"]. |
| GET /negocio/pedidos/{pedido_id:int}/faturar (perm. negocios.pedido:faturar) | **OK** | Rota existe; checagem "negocios.pedido:faturar" + Superadministrador. |
| GET /negocio/relatorio-conversao-orcamentos (perm. negocios.orcamento:visualizar) | **OK** | Rota existe; checagem correspondente. |
| Ordem: /novo antes de /{id}/editar | **OK** | orcamentos/novo antes de orcamentos/{id}/editar; idem para pedidos. |
| check_html_module_permission(..., "negocios", ...) + checagem em context | **OK** | Padrão usado em todas; get_user_with_permissions retorna modulos + nomes, então "negocios" está em perms quando há permissão do módulo. |

---

### 2.7 Templates (Jinja2)

| Requisito | Status | Verificação |
|-----------|--------|-------------|
| meu_negocio/orcamentos/index.html (listagem, filtro status, badges, links Novo/Editar/PDF) | **OK** | Template existe; link para relatório de conversão. |
| meu_negocio/orcamentos/form.html (estabelecimento, destinatário, validade, itens, modal produto) | **OK** | Template existe. |
| meu_negocio/pedidos/index.html (listagem, links Novo/Editar/Faturar/PDF) | **OK** | Template existe; link para relatório de conversão. |
| meu_negocio/pedidos/form.html (estabelecimento, orçamento opcional, itens) | **OK** | Template existe. |
| meu_negocio/pedidos/faturar.html (itens com qtd a faturar, submit para API faturar) | **OK** | Template existe. |
| meu_negocio/relatorio_conversao_orcamentos.html (filtros data, resposta da API) | **OK** | Template existe. |
| Chamadas de API: /api/v1/orcamentos, /api/v1/pedidos, /api/v1/relatorios/conversao-orcamentos, /api/v1/produtos-cliente/, /api/v1/clientes/todos | **OK** | Verificado nos templates (form, index, relatorio). |

---

### 2.8 Sidebar

| Requisito | Status | Verificação |
|-----------|--------|-------------|
| Item Orçamentos: link /negocio/orcamentos | **OK** | sidebar.html com href="/negocio/orcamentos". |
| Visível quando negocios.orcamento:visualizar em user_permissions ou user_role == 'Superadministrador' | **OK** | Condição: `user_permissions and 'negocios.orcamento:visualizar' in user_permissions or user_role == 'Superadministrador'`. |
| Item Pedidos: link /negocio/pedidos | **OK** | href="/negocio/pedidos". |
| Visível quando negocios.pedido:visualizar ou Superadministrador | **OK** | Condição análoga. |
| Padrão sidebar-item e data-feather | **OK** | file-plus e shopping-cart; classe sidebar-item. |

---

### 2.9 Verificações finais e dependências (seção 9)

| Requisito | Status | Verificação |
|-----------|--------|-------------|
| Cookie: pdv_solumatica_token (e pdv_automscale_token nos templates) | **OK** | Templates do módulo usam ambos os nomes no getToken(). |
| GET /api/v1/clientes/todos existe | **OK** | clientes.py com @router.get("/todos"). |
| GET /api/v1/produtos-cliente/?cliente_id=... (prefix com hífen) | **OK** | produtos_cliente.py com prefix "/produtos-cliente"; templates usam /api/v1/produtos-cliente/. |
| Email/WhatsApp: orcamentos.py tem enviar-email e enviar-whatsapp; services existem | **OK** | Endpoints existem; EmailService e whatsapp_service (enviar_mensagem_whatsapp) em app/services. |

---

### 2.10 Armadilhas (seção 10) — aplicação no código

| Item do plano | Status | Verificação |
|---------------|--------|-------------|
| WeasyPrint lazy + ImportError/OSError | **OK** | pdf_orcamento_pedido._html_to_pdf. |
| ROUTER_INCLUDE com orcamentos e pedidos | **OK** | main.py. |
| Relatório conversão: datetime.combine para datas | **OK** | relatorios.py. |
| Cancelar pedido: refazer get do Pedido após liberar_reserva | **OK** | pedidos.py: liberar_reserva(db, pedido_id); em seguida p = _pedido_no_escopo(...); p.status = "cancelado"; commit. |
| PUT orçamento sem cliente_id no schema | **OK** | OrcamentoUpdate não inclui cliente_id; front pode enviar; backend ignora. |
| Templates com URL /api/v1/produtos-cliente/ (hífen) | **OK** | Verificado. |
| Seed: INSERT permissão só se não existir; nomes das roles | **OK** | _insert_permissao com SELECT 1; ROLES_COM_PERMISSAO com nomes exatos. |
| __init__.py: pedido antes de orcamento | **OK** | Ordem confirmada. |
| Relationships sem back_populates (Orcamento ↔ Pedido) | **OK** | orcamento.py e pedido.py conferidos. |

---

### 2.11 Verificações finais (seção 11) e Checklist (seção 12)

| Item | Status | Observação |
|------|--------|-------------|
| Alembic upgrade head | **OK** | Executável; head atual sa_ww33xx137n3x1. |
| Imports (models, core, database) | **OK** | Teste de importação realizado. |
| Permissões na base e acesso com Cliente Administrador | **Observação** | Verificação manual; seed está correto. |
| Testes de APIs (GET listagens, POST orçamento/pedido, POST faturar) | **Observação** | Verificação manual recomendada. |
| NotaFiscal com pedido_id e origem_documento no faturar_pedido | **OK** | pedido_service.faturar_pedido cria NF com pedido_id e OrigemDocumentoFiscalEnum.ORCAMENTO. |

---

## 3. Listagem de pendências

Lista de itens pendentes de implementação (a implementar no código):

1. *(nenhum)*

**Nenhuma pendência de implementação foi encontrada.** Todos os requisitos das seções 1 a 12 do plano que são passíveis de verificação no código estão atendidos no projeto `solumatica_auto`. As únicas atividades não automatizadas são as verificações manuais da seção 11 (testes com usuário Cliente Administrador e chamadas às APIs), que não configuram pendência do plano em si.

---

## 4. Resumo

| Categoria | Total verificado | OK | Pendência | Observação |
|-----------|------------------|-----|-----------|------------|
| Banco (1.1, 1.2) | 8 | 8 | 0 | 0 |
| Models | 8 | 8 | 0 | 0 |
| Schemas | 2 | 2 | 0 | 0 |
| Services | 5 | 5 | 0 | 0 |
| APIs | 7 | 7 | 0 | 0 |
| Rotas HTML | 10 | 10 | 0 | 0 |
| Templates | 7 | 7 | 0 | 0 |
| Sidebar | 5 | 5 | 0 | 0 |
| Deps/Integração | 4 | 4 | 0 | 0 |
| Armadilhas/Checklist | 9 | 9 | 0 | 0 |
| **Total** | **65** | **65** | **0** | **2 (manuais)** |

**Conclusão:** A implementação está aderente ao plano. Não há pendências a implementar no código; recomenda-se apenas executar os testes manuais descritos na seção 11 do plano (acesso com Cliente Administrador e chamadas às APIs).
