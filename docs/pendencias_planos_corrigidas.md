# Análise dos planos — pendências identificadas e correções

Documento gerado a partir do **Backlog técnico**, **Refinamentos** e **Análise de segurança e cobertura**.

---

## Correções realizadas

### F3 — Persistência rica WebhookEvent
- **Pendência:** O handler do webhook MP não gravava evento em `webhook_events`.
- **Correção:** No `app/api/webhooks_mercadopago.py`, antes de processar:
  - Idempotência por `event_key = mercadopago:payment:{payment_id}`.
  - Criação de `WebhookEvent` com `raw_json`, `headers_json`, `query_params_json`, `signature_valid`, `provider_payment_id`, `event_type`, `received_at`.
  - Após processar com sucesso: `processed_at`, `processing_attempts`, `payment_transaction_id`, `normalized_status`.
  - Em exceção: `last_processing_error` e incremento de `processing_attempts`.

### I1 — Billing ao confirmar pagamento
- **Pendência:** Nenhum evento em `billing_usage_events` ao aprovar pagamento marketplace.
- **Correção:** Em `webhook_marketplace_service.process_payment_notification`, quando status passa a paid/authorized, chamada a `record_payment_billing` (idempotente) com cliente, loja, pedido, itens e valor.

### I2 — Reversão de cobrança no estorno
- **Pendência:** Refund não registrava reversão em `billing_usage_events`.
- **Correção:** Em `refund_service.request_refund`, após estorno confirmado, chamada a `record_refund_reversal` com `source_refund_id`, `payment_transaction_id`, `cliente_id` e valor.

### Contexto único (Refinamento 1)
- **Pendência:** Garantir que PaymentTransaction de marketplace não tenha `venda_id`/`pdv_id`.
- **Correção:** Em `checkout_marketplace_service`, criação de `PaymentTransaction` com `venda_id=None` e `pdv_id=None` nos fluxos de checkout e retry.

### Documentação de segurança (Análise de segurança)
- **Pendência:** Regras de segurança e não-funcionais não estavam no documento de regras V1.
- **Correção:** Nova seção em `docs/regras_v1_pagamentos_marketplace.md`: redirect URL, credenciais, dados de pagamento, refund admin, OAuth e URL de webhook.

---

## Lacunas corrigidas (implementação posterior)

| Item | Correção aplicada |
|------|--------------------|
| **F2** | Router central em `app/api/webhooks_payments.py`: `POST /api/webhooks/payments/mercadopago` (delega ao handler MP), `POST /api/webhooks/payments/asaas`, `/pagarme`, `/stripe` (501). |
| **G2** | Task Celery `process_webhook_event_marketplace(webhook_event_id)`; função `process_webhook_event_by_id_sync(db, id)` em `webhooks_mercadopago` para reprocessamento/ fila assíncrona. |
| **C3** | Stubs em `app/services/payments/stubs/`: `asaas.py`, `pagarme.py`, `stripe.py`; registrados em `factory._provider_from_config` e em `ALLOWED_MARKETPLACE_PROVIDERS`. |
| **Rate limit webhook** | `webhook_rate_limiter` e `check_webhook_rate_limit` em `rate_limiter.py`; aplicado em `webhooks_mercadopago` e em `webhooks_payments`. |
| **Idempotency key checkout** | Campo `idempotency_key` em `pedidos_marketplace` (migração mp03); schema `PedidoCheckoutCreate.idempotency_key`; no checkout, devolve pedido existente (24h) quando chave repetida. |
| **Authz refund admin** | `POST /admin/audit-pagamentos/refund` exige `Depends(require_superadmin())` e repassa `current_user.id` como `requested_by_user_id`. |

---

## Status por fase (resumo)

| Fase | Status |
|------|--------|
| Bloco 0 | Documentado em `regras_v1_pagamentos_marketplace.md` |
| A1–A6, A4, A5 | Migrations e models implementados |
| B1–B4 | status_map, base, DTOs |
| C1, C2 | Provider MP + factory; C3 stubs genéricos |
| D1–D3 | checkout_service, retry, endpoint loja |
| E1, E2 | Serviço reserva + estados pedido |
| F1 (lógica) | process_payment_notification; **F2** router central opcional; **F3** corrigido |
| G1 (lógica) | Atualização tx/pedido no webhook; **G2** task opcional; **G3** job expire_reservations |
| H1, H2 | refund_service + endpoint admin |
| I1, I2 | billing_usage_service + chamadas ao aprovar/estornar (corrigido) |
| J1–J4 | Front implementado |
| K1–K3 | Painel auditoria (endpoints admin/audit-pagamentos) |
