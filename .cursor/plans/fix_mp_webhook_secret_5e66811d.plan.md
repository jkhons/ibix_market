---
name: Fix MP Webhook Secret
overview: Todos os webhooks do Mercado Pago estao falhando com `digest_mismatch` porque o webhook secret configurado no sistema nao corresponde ao configurado no painel do Mercado Pago. Isso afeta TODOS os pedidos da vitrine, nao apenas o 58-553.
todos:
  - id: fix-secret
    content: Atualizar MP_WEBHOOK_SECRET no .env com o secret correto do painel Mercado Pago e reiniciar a aplicação
    status: completed
  - id: reconcile-order
    content: Reconciliar manualmente o pedido 58-553 via endpoint POST /api/v1/payments/reconcile/{transaction_uuid}
    status: completed
  - id: auto-reconcile
    content: Criar task Celery de reconciliação automática para pedidos pendentes como fallback contra falhas de webhook
    status: completed
isProject: false
---

# Correção do Webhook Mercado Pago - Pedidos Pendentes

## Diagnóstico Confirmado

Os logs em `logs/pdv_solumatica.log` mostram que **100% dos webhooks do Mercado Pago estao sendo rejeitados** com `digest_mismatch`. Isso significa que o sistema recebe a notificação de pagamento do MP, mas a verificação de assinatura HMAC-SHA256 falha, e o pagamento nunca é confirmado.

Evidência dos logs (pedido do usuario, payment_id `151591233058`, hoje 23/03):

```
2026-03-23 12:59:46 - WARNING - reason=digest_mismatch
  received_v1_prefix=a3874cc75c  computed_v1_prefix=310c8663ed
```

O MP tentou enviar o webhook **varias vezes** (payment.created + payment.updated), todas falharam. O mesmo ocorre com pagamentos desde 19/03 pelo menos.

## Causa Raiz

O [.env](.env) tem `MP_WEBHOOK_SECRET` **comentado** (linha 33). O sistema busca o secret via `_candidate_webhook_secrets()` em [app/api/webhooks_mercadopago.py](app/api/webhooks_mercadopago.py) nesta ordem:

1. `get_mp_webhook_secret(db)` -- tabela billing_config no banco
2. `os.getenv("MP_WEBHOOK_SECRET")` -- vazio (comentado)
3. Credenciais de `PaymentProviderConfig` (campo `webhook_secret` no JSON encriptado)

Algum desses retorna um secret, mas ele **nao corresponde** ao secret configurado no painel do Mercado Pago (Integrações > Webhooks). Por isso o HMAC calculado difere do HMAC enviado pelo MP.

## Solução Imediata - Corrigir o Secret

### Passo 1: Obter o Webhook Secret correto do Mercado Pago

1. Acessar [Mercado Pago Developers](https://www.mercadopago.com.br/developers/panel/app) com a conta `user_id: 338366730`
2. Em **Integrações > Webhooks**, copiar o **Secret Key** exibido para o webhook configurado na URL `https://www.solumatica.com.br/api/webhooks/mercadopago`
3. Se nao houver webhook configurado, criar um apontando para `https://www.solumatica.com.br/api/webhooks/mercadopago?source_news=webhooks` com evento `payment`

### Passo 2: Atualizar o secret no sistema

Opcao A (`.env`): Descomentar e preencher em [.env](.env):

```
MP_WEBHOOK_SECRET=<secret_do_painel_mp>
```

Opcao B (banco): Atualizar via Admin Billing a configuração `billing_mp_webhook_secret` ou o campo `webhook_secret` dentro das credenciais encriptadas de `PaymentProviderConfig`.

### Passo 3: Reiniciar a aplicação para carregar o novo secret

### Passo 4: Reconciliar o pedido 58-553

Após corrigir o secret, usar o endpoint de reconciliação manual que ja existe:

```
POST /api/v1/payments/reconcile/{transaction_uuid}
```

Esse endpoint em [app/api/v1/payments.py](app/api/v1/payments.py) (linha 190) consulta diretamente a API do MP pelo status real do pagamento e atualiza o pedido via `process_payment_notification()`, sem depender de webhook. Precisa do `transaction_uuid` do pedido 553 (obtido via banco ou lista de pagamentos no painel).

## Solução Sistêmica - Fallback Automático (opcional, recomendado)

Adicionar um mecanismo de reconciliação automática para que pedidos pendentes sejam verificados periodicamente, mesmo se o webhook falhar:

- Criar uma task Celery que rode a cada 5-10 minutos
- Busca `PedidoMarketplace` com `status_pagamento = "pendente"` e `created_at` nas ultimas 24h
- Para cada um, consulta a API do MP pelo `external_reference` (pedido_id)
- Se o pagamento for `approved`, chama `process_payment_notification()`
- Isso protege contra falhas de webhook, rotação de secrets, e instabilidades de rede

## Arquivos Envolvidos

- [.env](.env) -- secret comentado (linha 33)
- [app/api/webhooks_mercadopago.py](app/api/webhooks_mercadopago.py) -- handler do webhook e `_candidate_webhook_secrets()`
- [app/integrations/mercadopago.py](app/integrations/mercadopago.py) -- `verify_webhook_signature()` e `MercadoPagoClient`
- [app/services/payments/webhook_marketplace_service.py](app/services/payments/webhook_marketplace_service.py) -- `process_payment_notification()`
- [app/api/v1/payments.py](app/api/v1/payments.py) -- endpoint `/reconcile/{transaction_uuid}` (linha 190)
- [app/services/payments/checkout_marketplace_service.py](app/services/payments/checkout_marketplace_service.py) -- criacao do checkout e PaymentTransaction

