# Checklist — Guest Checkout e Integração CRM

Checklist de validação da implementação (checkout guest, consumidor GUEST, numero_pedido, eventos, API integração, gestão).

---

## 1. Migration e modelos

- [ ] Migration `mk03_guest` aplicada sem erro (`alembic upgrade mk03_guest`)
- [ ] Tabela `integration_events` existe
- [ ] Colunas novas em `consumidores_marketplace`: `tenant_id`, `tipo_consumidor`, `status_cadastro`, `aceite_marketing`, UTMs, `deleted_at`; `senha_hash` nullable
- [ ] Colunas novas em `pedidos_marketplace`: `tenant_id`, `numero_pedido`, `status_entrega`, `origem_pedido`, `aceite_marketing_snapshot`, UTMs
- [ ] Colunas novas em `pedido_itens_marketplace`: `tenant_id`, `loja_id`, `nome_produto_snapshot`, snapshots
- [ ] Model `IntegrationEvent` importável e registrado em `app.models`

---

## 2. Checkout (API e fluxo)

- [ ] POST `/api/v1/loja/checkout` com loja ativa e anúncio publicado cria pedido
- [ ] Resposta do checkout contém `numero_pedido` (formato ex.: `tenant_id-id`)
- [ ] Resposta contém `status_entrega`, `comprador_email`
- [ ] Sempre existe `comprador_id` no pedido (find-or-create GUEST por tenant+email)
- [ ] Body aceita `aceite_marketing`, `utm_source`, `utm_medium`, `utm_campaign`, `observacoes_cliente`
- [ ] Itens do pedido gravam `nome_produto_snapshot` (e demais snapshots quando aplicável)

---

## 3. Eventos de integração

- [ ] Ao criar consumidor GUEST no checkout: evento `consumer.created` em `integration_events`
- [ ] Ao criar pedido: evento `order.created` em `integration_events`
- [ ] Ao completar cadastro (GUEST → REGISTERED): evento `consumer.registered`
- [ ] Ao alterar `aceite_marketing` no PUT minha-conta: evento `consumer.marketing_optin_changed`

---

## 4. Completar cadastro

- [ ] POST `/api/v1/loja/completar-cadastro` com `email`, `numero_pedido`, `senha` (mín. 6) atualiza consumidor GUEST
- [ ] E-mail deve coincidir com o do pedido; pedido deve existir
- [ ] Consumidor fica com `tipo_consumidor=REGISTERED`, `status_cadastro=COMPLETO`, `senha_hash` preenchido
- [ ] Página `/loja/completar-cadastro` carrega (200) e aceita query `?email=...&numero_pedido=...`

---

## 5. Consulta pública de pedido

- [ ] GET `/api/v1/loja/pedido/consultar?numero_pedido=...&email=...` retorna resumo do pedido
- [ ] Retorna `numero_pedido`, `status_pedido`, `status_pagamento`, `status_entrega`, `total`, `itens`
- [ ] 403 se e-mail não coincidir com o do pedido; 404 se pedido não existir
- [ ] Página `/loja/acompanhar-pedido` carrega (200)

---

## 6. API de integração CRM

- [ ] GET `/api/integracao/health` sem Bearer retorna 401
- [ ] GET `/api/integracao/health` com Bearer inválido retorna 403
- [ ] Sem `INTEGRATION_TOKEN` no ambiente, retorna 503 ao usar Bearer
- [ ] Com `INTEGRATION_TOKEN` e Bearer correto: `GET /api/integracao/health` retorna 200
- [ ] GET `/api/integracao/consumidores` (com token) retorna estrutura paginada `items`, `next_cursor`, `limit`
- [ ] GET `/api/integracao/pedidos` (com token) retorna lista com `numero_pedido` nos itens
- [ ] GET `/api/integracao/eventos` (com token) retorna lista de eventos

---

## 7. Front (vitrine e gestão)

- [ ] Página `/loja/checkout` exibe checkbox "Aceito receber ofertas" (LGPD) e campo observações
- [ ] Redirect pós-checkout vai para `/loja/obrigado?numero_pedido=...&pedido_id=...&email=...`
- [ ] Página `/loja/obrigado` exibe numero do pedido e link "Criar conta" quando há `email` na URL
- [ ] Página `/negocio/marketplace/consumidores` carrega (com auth e permissão) e lista consumidores
- [ ] Página `/negocio/marketplace/integracao/eventos` carrega e lista eventos
- [ ] Listagem de pedidos da loja (gestão) exibe `numero_pedido` e `status_entrega`

---

## 8. Cadastro e login com tenant

- [ ] POST cadastro aceita `loja_id` opcional; consumidor criado com `tenant_id = loja.cliente_id`
- [ ] POST login aceita `loja_id` opcional; busca consumidor por tenant_id + email
- [ ] Login rejeita consumidor com `senha_hash` null (GUEST não logado)

---

## 9. PUT minha-conta

- [ ] PUT `/api/v1/loja/minha-conta` aceita `aceite_marketing` no body
- [ ] Ao alterar `aceite_marketing`, emite evento `consumer.marketing_optin_changed`

---

## 10. Testes automatizados

- [ ] `pytest tests/test_marketplace_loja.py -v -m "not refactor_home"` passa
- [ ] Testes de contrato para checkout (422 sem itens, 404 loja inexistente; 429 se rate limit)
- [ ] Teste de contrato para pedido/consultar (422 sem params, 404 pedido inexistente)
- [ ] Teste de contrato para completar-cadastro (400 senha curta, 422 body vazio; 429 se rate limit)
- [ ] Teste de contrato para API integração (401/503 sem Bearer, 403/503 Bearer inválido)
- [ ] Páginas HTML: completar-cadastro, acompanhar-pedido retornam 200

---

## Como rodar os testes (pé quente)

```bash
cd /central_solumatica/pdv_solumatica
.venv/bin/pytest tests/test_marketplace_loja.py -v
```

Para rodar só os testes rápidos (excluindo marcadores opcionais):

```bash
.venv/bin/pytest tests/test_marketplace_loja.py -v -m "not refactor_home"
```
