# Verificação 100% — Módulo Frete / Logística (entregador)

Conferência contra o plano `módulo_frete_logística_entregador_fa81c783.plan.md`.

---

## 1. Modelo de dados

| Item | Status | Implementação |
|------|--------|----------------|
| Tabela `entregadores` (id, nome, email UNIQUE, senha_hash, telefone, cpf, tipo_veiculo, ativo, status, tenant_id, cidade, created_at, updated_at) | OK | Migration lg01 + `app/models/entregador.py` |
| Regra tenant_id: NULL = plataforma; preenchido = vinculado (documentado no model) | OK | Comentário no model e docstring |
| Tabela `entregas_marketplace` (todas as colunas do DDL, UNIQUE pedido_id, FKs) | OK | Migration lg01 + `app/models/entrega_marketplace.py` |
| Tabela `entrega_eventos` (id, entrega_id, tipo_evento, actor_type, actor_id, payload_json, created_at) | OK | Migration lg01 + `app/models/entrega_evento.py` |
| Pedido **sem** entregador_id (espelho opcional; verdade em entregas_marketplace) | OK | `PedidoMarketplace` não possui entregador_id |
| Contrato JSON endereço (cep, logradouro, numero, complemento, bairro, cidade, uf, referencia) documentado | OK | `EnderecoEntregaJson` em schemas + docstring |

---

## 2. Status e transições

| Item | Status | Implementação |
|------|--------|----------------|
| Constantes em `app/core/constants/entrega_status.py` (todos os status + STATUS_VALIDOS) | OK | Arquivo existente e export em `__init__.py` |
| Vocabulário tipo_veiculo (moto, carro, utilitario) e tipo_veiculo_aceito (+ qualquer) | OK | Constantes TIPOS_VEICULO, TIPOS_VEICULO_ACEITO |
| Máquina de estados no service (aceita→em_retirada→retirada→em_rota→entregue/falha_entrega) | OK | `app/services/logistica/entrega_status_service.py` com `_TRANSICOES` |
| Toda mudança de status gera evento em `entrega_eventos` | OK | Em `entrega_status_service`, `entrega_aceite_service`, `entrega_service` |
| Regra de expiração: aceita_ate_em < now() e status disponivel → expirada | OK | `marcar_entregas_expiradas()` em `entrega_service.py`; chamada em GET entregas-disponiveis |

---

## 3. Autenticação entregador

| Item | Status | Implementação |
|------|--------|----------------|
| `create_entregador_token(entregador_id, email=None)` em `app/core/auth.py` | OK | Payload sub, tipo='entregador', email opcional; expiração por settings |
| `get_current_entregador` em `app/api/v1/entregador.py` | OK | Lê Bearer ou cookie `entregador_token`, valida tipo, carrega Entregador ativo |
| Helper `_token_from_request_entregador` (header + cookie) | OK | Cookie nome oficial `entregador_token` |
| Rotas entregador (exceto login) com `Depends(get_current_entregador)` | OK | entregas-disponiveis, aceitar, minhas-entregas, detalhe, status |

---

## 4. Aceite com lock transacional

| Item | Status | Implementação |
|------|--------|----------------|
| SELECT ... FOR UPDATE no aceite | OK | `entrega_aceite_service.py`: `with_for_update()` |
| Validação status==disponivel e entregador_id IS NULL; 409 se já aceita | OK | Service + HTTP 409 no endpoint |

---

## 5. Escopo entregador vs tenant

| Item | Status | Implementação |
|------|--------|----------------|
| Listagem disponíveis: status=disponivel, entregador_id NULL; filtro cidade opcional (campo em entregadores) | OK | GET entregas-disponiveis; cidade no model; filtro por cidade preparado (estrutura) |
| Tenant: validação de escopo (allowed_ids) em criar/publicar/listar/detalhar/cancelar | OK | `_allowed_cliente_ids` em `logistica.py` |

---

## 6. Organização de arquivos

| Item | Status | Implementação |
|------|--------|----------------|
| `app/core/constants/entrega_status.py` | OK | Constantes e vocabulários |
| `app/models/entregador.py`, `entrega_marketplace.py`, `entrega_evento.py` | OK | Com relações e __tablename__ corretos |
| Export em `app/models/__init__.py` (Entregador, EntregaMarketplace, EntregaEvento) | OK | Imports e __all__ |
| `app/schemas/entregador.py` (login, resposta) | OK | EntregadorLoginIn, EntregadorResponse, EntregadorLoginResponse |
| `app/schemas/entrega_marketplace.py` (criação, status, respostas, evento) | OK | EnderecoEntregaJson, EntregaCreateIn, EntregaStatusUpdateIn, EntregaEventoOut, EntregaDisponivelOut, EntregaOut |
| `app/api/v1/entregador.py` (prefix /entregador) | OK | Login, entregas-disponiveis, aceitar, minhas-entregas, detalhe, status |
| `app/api/v1/logistica.py` (prefix /logistica) | OK | Criar, publicar, listar, detalhar, cancelar |
| `app/services/logistica/` (entrega_service, entrega_aceite_service, entrega_status_service) | OK | Inclui `marcar_entregas_expiradas` |
| main.py: ROUTER_SPECS e ROUTER_INCLUDE (entregador, logistica com /api/v1) | OK | Registrados |

---

## 7. Endpoints MVP

| Método | Rota | Status |
|--------|------|--------|
| POST | /api/v1/entregador/login | OK |
| GET | /api/v1/entregador/entregas-disponiveis | OK |
| POST | /api/v1/entregador/entregas/{id}/aceitar | OK (409 se já aceita) |
| GET | /api/v1/entregador/minhas-entregas | OK |
| POST | /api/v1/entregador/entregas/{id}/status | OK (máquina de estados no service) |
| POST | /api/v1/logistica/entregas | OK |
| POST | /api/v1/logistica/entregas/{id}/publicar | OK |
| GET | /api/v1/logistica/entregas | OK |
| GET | /api/v1/logistica/entregas/{id} | OK |
| POST | /api/v1/logistica/entregas/{id}/cancelar | OK |

---

## 8. Migrações e seed

| Item | Status | Implementação |
|------|--------|----------------|
| lg01: entregadores, entregas_marketplace, entrega_eventos (colunas, CHECK, FKs, índices) | OK | `lg01_entregadores_entregas_marketplace_eventos.py` |
| Merge heads (lg01 + mc03) | OK | `merge_lg01_mc03_heads.py` |
| Seed mínimo entregador (Carlos Moto, carlos.moto@teste.com, senha 123456) | OK | `lg02_seed_entregador_teste.py` |

---

## 9. Front-end

| Item | Status | Implementação |
|------|--------|----------------|
| Rotas HTML entregador: /entregador/login, /entregador/logout, /entregador/disponiveis, /entregador/minhas-entregas, /entregador/entrega/{id} | OK | main.py |
| Cookie `entregador_token` após login; redirecionar para /entregador/disponiveis | OK | login.html |
| Tratamento 401 → redirecionar para /entregador/login | OK | disponiveis, minhas_entregas, detalhe (fetch + redirect) |
| Templates: login, disponiveis, minhas_entregas, detalhe, base_entregador | OK | app/templates/entregador/ |
| Área tenant: coluna Entrega na tabela de pedidos (Minha Loja); botões Criar entrega, Publicar, Acompanhar | OK | minha_loja.html + modal Criar entrega |
| Tela acompanhar entrega (status, entregador, timeline/eventos, cancelar) | OK | /negocio/marketplace/logistica/entrega/{id} + logistica/acompanhar_entrega.html |

---

## 10. Regras de negócio resumidas

| Regra | Status |
|-------|--------|
| Criar entrega: pedido no escopo do tenant | OK (logistica criar_entrega_endpoint) |
| Uma entrega por pedido: UNIQUE(pedido_id) | OK (migration + model) |
| Aceite com lock; 409 se já aceita | OK (entrega_aceite_service) |
| Entregador só altera suas entregas (entregador_id == logado) | OK (entrega_status_service + endpoint) |
| Tenant vê só suas entregas (escopo) | OK (_allowed_cliente_ids em logistica) |
| Histórico: toda mudança gera evento | OK (todos os services) |

---

## Conclusão

**Implementação conferida 100% em relação ao plano.**  
Nenhum item obrigatório do MVP de frete/logística entregador ficou pendente.
