# Validação técnica — implementação de pagamentos marketplace

**Papel:** Consultor técnico  
**Escopo:** Arquitetura de pagamentos (checkout, webhook, reserva, billing, refund, auditoria)  
**Data:** 2026-03-10  

---

## 1. Resumo executivo

Foi feita uma revisão ponta a ponta da implementação. **Foi encontrado e corrigido 1 bug crítico** (webhook não encontrava transação de marketplace) e **4 melhorias de segurança/robustez** aplicadas. O restante da implementação está consistente e em boa condição.

---

## 2. Correções aplicadas nesta validação

### 2.1 Bug crítico: webhook não encontrava transação (marketplace)

**Problema:** A função `_find_transaction_by_external_reference` buscava apenas por `"idempotency_key": "{valor}"` no JSON de `provider_response`. No checkout do marketplace o sistema grava `"external_reference": "{pedido_id}"` (e não `idempotency_key`). Com isso, o webhook do Mercado Pago nunca encontrava a transação e o pagamento aprovado não atualizava pedido/reserva/billing.

**Correção:** Em `app/api/webhooks_mercadopago.py` a função foi reescrita para:
1. **Marketplace:** Se `external_reference` for numérico, buscar primeiro por `PaymentTransaction.pedido_id == valor` e `provider_code == "mercadopago"`.
2. **Fallback:** Buscar no JSON por `"external_reference"` ou `"idempotency_key"` com o valor (fluxo PDV/legado).

**Arquivo:** `app/api/webhooks_mercadopago.py` — `_find_transaction_by_external_reference`.

---

### 2.2 Segurança: endpoints de auditoria desprotegidos

**Problema:** Os GETs `/admin/audit-pagamentos/transacoes`, `/webhooks` e `/refunds` não exigiam autenticação. Qualquer um poderia listar transações, webhooks e estornos.

**Correção:** Todos os três endpoints passaram a usar `Depends(require_superadmin())`, alinhados ao POST `/refund` e a outros painéis admin (ex.: `admin_billing`).

**Arquivo:** `app/api/v1/admin_audit_pagamentos.py`.

---

### 2.3 Rastreabilidade: reversão de billing no estorno

**Problema:** `record_refund_reversal` não preenchia `loja_id` nem `pedido_id` no `BillingUsageEvent`, dificultando relatórios e conciliação.

**Correção:** Assinatura de `record_refund_reversal` ampliada com `loja_id` e `pedido_id` opcionais. Em `refund_service.request_refund`, ao chamar a função, são passados `loja_id` e `pedido_id` obtidos da transação/pedido.

**Arquivos:** `app/services/payments/billing_usage_service.py`, `app/services/payments/refund_service.py`.

---

### 2.4 Observabilidade: falhas silenciosas em billing

**Problema:** Exceções em `record_payment_billing` (webhook) e `record_refund_reversal` (refund) eram engolidas com `except Exception: pass`, sem log.

**Correção:** Uso de `log_error(..., exc_info=e)` nesses blocos para que falhas de billing/reversão apareçam em log e possam ser investigadas.

**Arquivos:** `app/services/payments/webhook_marketplace_service.py`, `app/services/payments/refund_service.py`.

---

### 2.5 Robustez: idempotência no checkout

**Problema:** Na devolução do pedido existente (idempotency key), a variável `tx` poderia não estar definida quando não houvesse transação ativa, gerando `NameError` ao montar `transaction_uuid`.

**Correção:** Inicialização explícita `tx = None` antes do bloco que busca a transação ativa.

**Arquivo:** `app/api/v1/loja.py` — endpoint de checkout.

---

## 3. Pontos validados (sem alteração)

| Área | Status | Observação |
|------|--------|------------|
| **Contexto único** | OK | `PaymentTransaction` de marketplace criada com `venda_id=None`, `pdv_id=None`. |
| **Idempotência WebhookEvent** | OK | Uso de `event_key` e `processed_at` evita processamento duplicado. |
| **Idempotência BillingUsageEvent** | OK | `payment_confirmed` por `payment_transaction_id`; reversão por `source_refund_id`. |
| **Reserva de estoque** | OK | Commit/liberação no webhook; job Celery para expiração; liberação por pedido único em `expire_reservations`. |
| **Rate limit webhook** | OK | `check_webhook_rate_limit` aplicado em ambos os routers de webhook. |
| **Authz refund** | OK | POST `/admin/audit-pagamentos/refund` exige `require_superadmin()` e repassa `requested_by_user_id`. |
| **Router central F2** | OK | `/api/webhooks/payments/mercadopago` delega; asaas/pagarme/stripe retornam 501. |
| **Stubs C3** | OK | Asaas, Pagar.me, Stripe em arquivos próprios e registrados na factory. |
| **Task G2** | OK | `process_webhook_event_marketplace(webhook_event_id)` e `process_webhook_event_by_id_sync` para reprocessamento. |
| **Mapeamento de status** | OK | `status_map` e `can_transition` usados de forma consistente. |
| **Assinatura webhook MP** | OK | Validação HMAC com secrets de config e global; 401 sem assinatura válida. |

---

## 4. Recomendações implementadas (correções posteriores)

- **Webhook assíncrono opcional:** Com `USE_WEBHOOK_ASYNC=true`, o handler persiste o `WebhookEvent`, faz commit, enfileira `process_webhook_event_marketplace.delay(webhook_ev.id)` e retorna 200 com `{"status": "ok", "queued": true}`. Sem a variável, o processamento continua síncrono.
- **Testes automatizados:** Em `tests/test_webhook_payments.py`: testes para `_find_transaction_by_external_reference` (vazio, numérico inexistente, numérico por `pedido_id`) e para o schema `PedidoCheckoutCreate` com e sem `idempotency_key`.
- **Métricas Prometheus:** Em `app/core/webhook_metrics.py`: contadores `pdv_webhook_received_total`, `pdv_webhook_processed_total`, `pdv_webhook_signature_invalid_total`, `pdv_webhook_processing_error_total`, `pdv_webhook_queued_total` (label `provider`). Incrementados no handler do webhook MP; expostos em `/metrics`.

---

## 5. Conclusão

A implementação está em **boa condição** para uso em produção após as correções desta validação. O bug do webhook que impedia a reconciliação de pagamentos marketplace foi corrigido; segurança dos endpoints de auditoria, rastreabilidade de reversões e observabilidade de falhas de billing foram reforçadas.
