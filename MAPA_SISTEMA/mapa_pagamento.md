# Mapa de Pagamentos — PDV Ibix

Este documento é a **fonte única de verdade** sobre pagamentos e gateways no sistema: cobrança de assinatura SaaS, pagamentos de vendas (PDV/loja), hierarquia de permissões e onde cada informação está distribuída.

**Referências cruzadas:** RBAC em `MAPA_RBAC.md`; endpoints em `MAPA_DE_API.md` (§ 17 e billing); regras em `MAPA_DE_REGRAS.md` (§ 14); arquitetura em `MAPA_DO_SISTEMA.md`.

---

## 1. Visão geral: dois fluxos de pagamento

| Fluxo | Quem paga | Quem recebe | Gateway / meio | Finalidade |
|-------|-----------|------------|----------------|------------|
| **Assinatura SaaS** | Cliente Administrador (tenant) | Central (SuperAdministrador) | Mercado Pago Checkout Pro (token global) | Mensalidade do sistema (trial, ativa, inadimplente, bloqueada) |
| **Vendas (PDV / loja)** | Cliente final na loja | Estabelecimento (CA) | Mercado Pago (ou outro) por estabelecimento | Pagamento da venda (dinheiro, cartão, PIX, boleto, etc.) |

- **SuperAdministrador** gerencia cobranças da assinatura (recebe do CA via central).
- **Cliente Administrador (CA)** paga a assinatura do seu tenant e **vende na loja**; pode configurar gateway por estabelecimento para receber pagamentos das vendas.

---

## 2. Hierarquia de permissões e pagamentos

### 2.1 SuperAdministrador

- **Recebe do CA:** Cobrança de assinatura é feita pela **central**. O SA acessa **Cobranças (Admin)** e gerencia todos os tenants (status, vencimento, gerar cobrança, bloquear/desbloquear).
- **Permissões de pagamento (assinatura):**
  - Menu **Cobranças (Admin)** → `/admin/billing/tenants`, detalhe do tenant, **Valor e descontos** (`/admin/billing/preco`), **Preços PDV** (`/admin/billing/precos-pdv`), **Códigos de desconto** (`/admin/billing/codigos-desconto`), **Config** (Mercado Pago e APP_URL).
  - Configura token MP global (billing), valor mensal, descontos, códigos promocionais, contratos comerciais, preços de licença PDV.
- **Não vende na loja:** Vendas e gateway por estabelecimento são escopo do CA (cada CA configura seu gateway se quiser).

### 2.2 Cliente Administrador (CA)

- **Paga a assinatura:** Tenant do CA é o “pagador” (`resolve_tenant_pagador`). Acesso a **Assinatura** (`/financeiro/assinatura`): status, próximo vencimento, **Pagar agora**, histórico de pagamentos (somente leitura).
- **Vende na loja:** Estabelecimentos (clientes) do CA realizam vendas no PDV. O CA pode configurar **gateway por estabelecimento** (ex.: Mercado Pago) em **Pagamentos** para receber pagamentos de vendas (cartão, PIX, etc.).
- **Escopo:** Apenas estabelecimentos no seu escopo (`ClienteScope.allowed_ids`) podem ter configs de gateway listadas/criadas; cada CA configura seu próprio gateway por estabelecimento (opcional).

### 2.3 Quem paga o quê (resolve_tenant_pagador)

| Role | tenant_id usado para billing | Observação |
|------|-----------------------------|------------|
| **Cliente Administrador** | `current_user.tenant_id` | É o pagador da assinatura. |
| **Subcliente / Técnico / Contador** | tenant do CA ao qual estão vinculados | `get_current_cliente_admin_id` → `usuarios.tenant_id` do CA. |
| **Superadministrador / Administrador** | — | Não aplica bloqueio por assinatura (sem tenant de cobrança). |

**Implementação:** `app/core/scope.py` — `resolve_tenant_pagador(db, user_id, role_nome)` retorna `tenant_id` ou `None`.

### 2.4 Quando a assinatura está bloqueada

- **SubscriptionGuard:** Rotas fora da **allowlist** retornam 403 (API) ou redirecionam para `/financeiro/assinatura` (HTML).
- **Sidebar:** Exibe apenas o item **Assinatura** (e brand); demais itens do menu ficam ocultos.
- **Variável de contexto:** `subscription_blocked` (calculada via `is_subscription_blocked(db, user)`).

### 2.5 CA: como recebe o pagamento hoje e onde configura o gateway

#### Onde o dinheiro cai

O valor vai para a **conta Mercado Pago** cujas credenciais (Access Token) estão na **configuração de gateway do estabelecimento**. Essa config é por estabelecimento (por `cliente_id`), e o CA só vê/edita estabelecimentos do seu escopo.

#### Fluxo no sistema

1. Na **venda** (PDV ou Nova Venda), ao finalizar com forma cartão/PIX (etc.), o front chama **POST** `/api/v1/payments/process` (estabelecimento, venda, valor, método, idempotency_key).
2. O backend usa a config ativa do estabelecimento em **payment_provider_configs**, chama o provedor (Mercado Pago), cria/atualiza **payment_transactions** e, quando o pagamento é aprovado no MP, o webhook **POST** `/api/webhooks/mercadopago` atualiza status da transação e sincroniza/cria **venda_pagamentos** para aquela venda.
3. O CA “recebe” no sistema quando a transação fica **paid/authorized** e o **venda_pagamento** correspondente fica **confirmado**; o dinheiro de fato cai na conta MP ligada às credenciais da config daquele estabelecimento.

#### Onde o CA acompanha

- **Recebíveis** (`/negocio/recebiveis`): lista de **configurações de gateway** por estabelecimento e lista de **transações** (pendentes/falhas/retentativa) via **GET** `/api/v1/payments/transactions`.
- **Vendas:** cada venda tem seus pagamentos fracionados em **venda_pagamentos** (forma, valor, status, id_externo), acessíveis pela tela de vendas e por **GET/POST** `/api/v1/venda-pagamentos/?venda_id=...`.

**Resumo:** o CA recebe o pagamento na conta Mercado Pago cujas credenciais estão na config do estabelecimento; no sistema, isso aparece como transações em **Recebíveis** e como **venda_pagamentos** nas vendas.

#### Onde o CA configura o gateway

| Aspecto | Detalhe |
|--------|---------|
| **Menu** | Negócios → **Recebíveis** (sidebar: ícone dollar-sign, link Recebíveis). |
| **URL** | `/negocio/recebiveis` (e `/negocio/pagamentos` redireciona para ela). |
| **Tela** | Seleção de **estabelecimento (cliente)** no topo. Tabela de configurações do estabelecimento: listagem via **GET** `/api/v1/payments/configs?estabelecimentoId=<id>`. Botão **“Nova configuração”** abre o modal de nova config. No modal: Estabelecimento, Gateway (hoje só “Mercado Pago”), Credenciais (JSON) (opcional), Ativo, Padrão, Modo teste; ao salvar chama **POST** `/api/v1/payments/configs` com `cliente_id`, `provider_code`, `credentials`, etc. |
| **Permissão** | Usuário precisa de alguma permissão de negócios (`negocios.venda:visualizar` ou `negocios.financeiro:visualizar` ou `negocios`). |
| **Escopo** | Só aparecem estabelecimentos do **escopo do CA** (`ClienteScope.allowed_ids`); a API de configs valida `estabelecimento_id` / `cliente_id` contra esse escopo. |

Ou seja: o CA configura o gateway em **Negócios → Recebíveis**, escolhendo o estabelecimento e cadastrando/alterando a integração (hoje só Mercado Pago) com credenciais e opções ativo/padrão/teste.

---

## 3. Gateways de pagamento no sistema

### 3.1 Gateway de assinatura (billing)

| Aspecto | Detalhe |
|--------|---------|
| **Provedor** | **Mercado Pago** (Checkout Pro) |
| **Configuração** | Global: tabela **configuracoes** (chaves `billing_mp_access_token`, `billing_mp_webhook_secret`, `billing_app_url`) ou variáveis de ambiente `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`, `APP_URL`. |
| **Uso** | Gerar preferência (Pay Now) → retorna `init_point` → usuário paga no MP (Pix, Cartão, Boleto). Confirmação via webhook e **GET** `https://api.mercadopago.com/v1/payments/{id}`. |
| **Validação do token** | GET `/api/v1/admin/billing/config/validate` chama API MP (`GET api.mercadolibre.com/users/me`). Badge "Mercado Pago: Conectado" na lista de tenants só aparece com token válido. |

### 3.2 Gateway de vendas (por estabelecimento)

| Aspecto | Detalhe |
|--------|---------|
| **Provedor (Fase 1)** | **Somente `mercadopago`** — API `/payments/configs` rejeita outros providers. |
| **Configuração** | Por estabelecimento: tabela **payment_provider_configs** (`cliente_id`, `provider_code`, `credentials_encrypted`, `fee_configs`, `routing_rules`, `is_active`, `is_default`, `test_mode`). |
| **Escopo** | Restrito ao tenant do CA: apenas estabelecimentos em `ClienteScope.allowed_ids` podem listar/criar configs; cada CA configura seu próprio gateway por estabelecimento (opcional). |
| **Fluxo** | Finalizar venda → criar venda → processar gateway em **POST** `/api/v1/payments/process`. Retentativa: **POST** `/api/v1/payments/retry/{transaction_uuid}`. |
| **Webhook** | **POST** `/api/webhooks/mercadopago` — valida assinatura (global ou por config ativa); primeiro tenta reconciliar **pagamento de venda** (external_reference = idempotency_key da transação); depois mantém fluxo de billing. |

### 3.3 Provedores plugáveis (interface)

- Interface em `app/services/payments/providers.py`: `PaymentProvider` (charge, refund, get_status, supports_method).
- Métodos suportados: `credit`, `debit`, `pix`, `boleto`, `cash`, `transfer`.
- Fase 1 operacional: apenas **mercadopago**; credenciais por estabelecimento em `payment_provider_configs.credentials_encrypted` (criptografadas em `app/services/payments/credentials.py`).

---

## 4. Distribuição das informações de pagamento

### 4.1 Cobrança de assinatura (billing)

| Onde | O que |
|------|--------|
| **Tabelas** | `subscriptions`, `payments`, `precos_pdv`, `contrato_comercial`, `contrato_aditivos`, `codigos_desconto`, `divulgadores`, `divulgador_regras`, `webhook_events`, `billing_notificacoes`; configurações em **configuracoes** (chaves `billing_*`). |
| **APIs** | Cliente: `GET/POST /api/v1/billing/*` (my-subscription, meus-limites, pay-now, my-payments). Admin: `GET/POST /api/v1/admin/billing/*` (tenants, tenant/{id}, create-charge, block, unblock, config, config/validate, preco, preco/aplicar-valor-todos). Preços PDV: `/api/v1/admin/precos-pdv/*`. Contratos: `/api/v1/contratos-comerciais/*`. Códigos: `/api/v1/codigos-desconto`, `/api/v1/divulgadores`. |
| **Webhook** | `POST /api/webhooks/mercadopago` — após reconciliar venda (se aplicável), chama `billing_service.process_payment_webhook`. |
| **Telas** | SA: `/admin/billing/tenants`, `/admin/billing/tenant/<id>`, `/admin/billing/config`, `/admin/billing/preco`, `/admin/billing/precos-pdv`, `/admin/billing/codigos-desconto`. CA/Subcliente: `/financeiro/assinatura`. |
| **Serviços** | `app/services/billing_service.py` (create_trial_subscription, create_checkout_preference, process_payment_webhook, process_billing_notifications, apply_grace_policy, _valor_centavos_para_tenant, _tenant_tem_desconto). |
| **Config** | `app/core/billing_config.py` (get_valor_mensal_centavos, get_desconto_*, get_mp_access_token, get_mp_webhook_secret, get_app_url). |

### 4.2 Pagamentos de venda (PDV / loja)

| Onde | O que |
|------|--------|
| **Tabelas** | `vendas` (tipo_pagamento, valor_pago, troco); **venda_pagamentos** (fracionamento: venda_id, forma, valor, status, id_externo); **payment_provider_configs** (gateway por estabelecimento); **payment_transactions** (transação unificada: uuid, cliente_id, venda_id, pdv_id, provider_code, status, amount, paid_at, reconciliation_*); **transaction_splits**, **split_rules**, **payment_logs**. |
| **APIs** | `POST/GET /api/v1/vendas` (criação de venda com tipo_pagamento/valor_pago/troco); `GET/POST /api/v1/venda-pagamentos` (listar/criar por venda_id, escopo por venda.cliente_id); `GET/POST /api/v1/payments/configs`, `POST /api/v1/payments/process`, `POST /api/v1/payments/retry/{transaction_uuid}`, `GET /api/v1/payments/status/{transaction_uuid}`, `GET /api/v1/payments/transactions`. |
| **Webhook** | `POST /api/webhooks/mercadopago` — reconcilia `payment_transactions` e sincroniza/cria **venda_pagamentos** para a venda vinculada. |
| **Telas** | PDV (Nova Venda), listagem de vendas; módulo **Pagamentos** (`/negocio/pagamentos`) para pendências e retentativa. |
| **Serviços** | `app/services/payments/orchestrator.py` (PaymentOrchestrator.process); `app/services/payments/providers.py` (get_provider, Mercado Pago); `app/services/payments/credentials.py` (encrypt/decrypt); `app/services/payments/split_engine.py`. |

### 4.3 Resumo por camada

- **Assinatura:** subscriptions + payments + configuracoes (billing_*) + rotas `/billing` e `/admin/billing` + SubscriptionGuard + job diário (notificações e bloqueio).
- **Vendas:** vendas + venda_pagamentos + payment_provider_configs + payment_transactions (+ splits/logs) + rotas `/vendas`, `/venda-pagamentos`, `/payments` + webhook MP (reconciliação venda).

---

## 5. Modelo de cobrança (assinatura)

| Regra | Descrição |
|-------|-----------|
| Trial | 30 dias a partir do cadastro (subscription.status = trial, period_end = hoje + 30, next_charge_at = period_end, grace_days = 15). |
| D0 | No dia do next_charge_at o status passa de trial para **inadimplente**. |
| Carência | 15 dias após next_charge_at; usuário ainda acessa; banner e botão "Pagar agora". |
| Bloqueio | Se hoje > next_charge_at + grace_days: subscription.status = bloqueada, **Tenant.ativo = False** (job diário). |
| Pagamento | Sempre manual: "Pagar agora" → preferência Checkout Pro → init_point (Pix, Cartão, Boleto). Confirmação via **GET** `/v1/payments/{id}` no MP (não confiar só no redirect). |

**Fluxo:** Cadastro → trial 30d → e-mails D-7, D-3, D-1, D0 → D0 inadimplente → e-mails D+1 … D+15 → pagando: webhook ativa/renova +30d; não pagando até D+15 → bloqueio.

---

## 6. Banco de dados (tabelas de pagamento)

### 6.1 Assinatura (billing)

| Tabela | Descrição |
|--------|-----------|
| **subscriptions** | Por tenant: tenant_id, plano_codigo, valor_mensal_centavos, qtd_pdvs_contratados, status (trial, ativa, inadimplente, bloqueada, cancelada), grace_days, period_start, period_end, next_charge_at, last_paid_at, blocked_at, mp_preference_id, last_payer_user_id. |
| **payments** | Rastreio MP por assinatura: subscription_id, mp_payment_id (único), status, amount_centavos, paid_at, external_reference, payer_user_id, raw_json. |
| **precos_pdv** | Licença PDV: valor_base_centavos, valor_pdv_adicional_centavos, vigencia_inicio, ativo. Fórmula: valor_mensal = base + (qtd - 1) × adicional. |
| **contrato_comercial** | Contrato SaaS por tenant: vigencia_inicio/fim, qtd_pdvs_contratados, valor_mensal_centavos, status. |
| **contrato_aditivos** | Aditivos ao contrato (qtd_pdvs, valor, motivo). |
| **codigos_desconto** | Código, tipo_promocao, descontos, ativo, divulgador_id. |
| **divulgadores** | Nome, cpf_cnpj, email, ativo, usuario_id. |
| **divulgador_regras** | Comissões por divulgador. |
| **webhook_events** | Idempotência webhook MP: provider, event_key (ex.: payment:{id}), received_at, processed_at, raw_json. UNIQUE(provider, event_key). |
| **billing_notificacoes** | Anti-spam e-mails: tenant_id, tipo (trial_d7, pastdue_d15, etc.), sent_at, canal. |

### 6.2 Vendas e gateway

| Tabela | Descrição |
|--------|-----------|
| **venda_pagamentos** | Fracionamento por venda: venda_id, forma (dinheiro, cartao_credito, pix, …), valor, status (pendente, confirmado, estornado), id_externo (gateway). |
| **payment_provider_configs** | Por estabelecimento (cliente_id): provider_code (mercadopago), credentials_encrypted, fee_configs, routing_rules, is_active, is_default, test_mode. |
| **payment_transactions** | Transação unificada: uuid, cliente_id, venda_id, pdv_id, provider_code, provider_transaction_id, payment_method, amount, status, paid_at, reconciliation_status, reconciliation_date. |
| **transaction_splits** | Splits por transação: recipient_type, recipient_id, original_amount, fee_amount, net_amount, status, settled_at. |
| **split_rules** | Regras de rateio (por estabelecimento/provedor). |
| **payment_logs** | Log por transação (auditoria). |

**Bloqueio:** SubscriptionGuard usa **Tenant.ativo**; quando subscription fica bloqueada, `Tenant.ativo = False`. `is_subscription_blocked(db, user)` usa tenant de `resolve_tenant_pagador`.

---

## 7. API (endpoints) — resumo

### 7.1 Cliente (CA / Subcliente) — assinatura

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/billing/my-subscription` | Status da assinatura (server_today, status, trial_days_left, grace_days_left, is_blocked, etc.). |
| GET | `/api/v1/billing/meus-limites` | Limites PDVs: max_pdvs, pdvs_usados, pdvs_disponiveis, valor_mensal_centavos. |
| POST | `/api/v1/billing/pay-now` | Gera preferência Checkout Pro; retorna init_point. |
| GET | `/api/v1/billing/my-payments?limit=50` | Histórico de pagamentos da assinatura. |

### 7.2 Super Admin — assinatura

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/admin/billing/tenants` | Lista tenants (status, vencimento, dias atraso). Query: `apenas_com_ca=true` para só tenants com CA. |
| GET | `/api/v1/admin/billing/tenant/{tenant_id}` | Detalhe do tenant. |
| POST | `/api/v1/admin/billing/tenant/{tenant_id}/create-charge` | Gera preferência e retorna init_point. |
| POST | `/api/v1/admin/billing/tenant/{tenant_id}/block` | Bloqueia (subscription + Tenant.ativo = False). |
| POST | `/api/v1/admin/billing/tenant/{tenant_id}/unblock` | Desbloqueia. |
| GET/POST | `/api/v1/admin/billing/config` | Config gateway (token, webhook secret, APP_URL). |
| GET | `/api/v1/admin/billing/config/validate` | Valida token no MP (badge "Conectado"). |
| GET/POST | `/api/v1/admin/billing/preco` | Valor mensal e descontos (escopo: todos, ca, admin_cliente, especifico). |
| POST | `/api/v1/admin/billing/preco/aplicar-valor-todos` | Aplica valor a todas as assinaturas (respeitar_codigos_promocionais). |
| GET/POST/PATCH | `/api/v1/admin/precos-pdv/*` | CRUD preços de licença PDV. |
| GET/POST | `/api/v1/contratos-comerciais/*` | Contratos e aditivos. |
| GET/POST/PATCH | `/api/v1/codigos-desconto`, `/api/v1/divulgadores` | Códigos e divulgadores. |

### 7.3 Pagamentos de venda (gateway por estabelecimento)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/v1/payments/configs?estabelecimentoId=` | Lista configs do estabelecimento (escopo CA). |
| POST | `/api/v1/payments/configs` | Cria config (Fase 1: só mercadopago). |
| POST | `/api/v1/payments/process` | Processa pagamento (estabelecimento_id, venda_id, amount, method, idempotency_key). |
| POST | `/api/v1/payments/retry/{transaction_uuid}` | Retenta transação pendente/falha. |
| GET | `/api/v1/payments/status/{transaction_uuid}` | Status da transação. |
| GET | `/api/v1/payments/transactions` | Lista transações (estabelecimentoId, status, data_inicio, data_fim). |
| GET/POST | `/api/v1/venda-pagamentos/?venda_id=` | Lista/cria pagamentos da venda (fracionamento). |

### 7.4 Webhook

- **POST** `/api/webhooks/mercadopago` — Sem JWT. Validação por headers **x-signature** e **x-request-id** (HMAC com secret global ou de config ativa). Idempotência por `webhook_events`. Processo: (1) Reconciliar pagamento de venda (payment_transactions + venda_pagamentos); (2) Se não for venda, processar billing (process_payment_webhook).

---

## 8. SubscriptionGuard e allowlist

**Arquivo:** `app/core/subscription_guard.py`.

**Allowlist (quando bloqueado):** `/financeiro/assinatura`, `/api/v1/billing/my-subscription`, `/api/v1/billing/pay-now`, `/billing/success`, `/billing/failure`, `/billing/pending`, `/auth/login`, `/logout`, `/static`.

---

## 9. Front (Jinja2 + JS)

- **Assinatura:** GET my-subscription retorna server_today, trial_days_left, grace_days_left, is_in_trial, is_past_due, is_blocked. Front não calcula datas; exibe só o que a API devolve.
- **Página Assinatura:** GET `/financeiro/assinatura` — template `financeiro/assinatura.html`; botão "Pagar agora" (POST pay-now → window.open(init_point)); histórico (GET my-payments).
- **Sidebar:** Se `subscription_blocked` → só item "Assinatura". Superadministrador → "Cobranças (Admin)" → `/admin/billing/tenants`.

---

## 10. E-mails automáticos e job diário

- **Job diário (Celery, 03:00):** `billing_daily_job` — apply_grace_policy + process_billing_notifications.
- **Anti-spam:** tabela **billing_notificacoes** (tenant_id, tipo, sent_at). Tipos: trial_d7, trial_d3, trial_d1, trial_d0; pastdue_d1, pastdue_d7, pastdue_d14, pastdue_d15.
- **D0:** E-mail trial_d0 e subscription.status = inadimplente.

---

## 11. Configuração (configuracoes e ambiente)

| Chave (configuracoes) | Descrição | Fallback env |
|----------------------|-----------|--------------|
| billing_mp_access_token | Access Token MP | MP_ACCESS_TOKEN |
| billing_mp_webhook_secret | Webhook Secret | MP_WEBHOOK_SECRET |
| billing_app_url | URL base da aplicação | APP_URL |
| billing_valor_mensal_centavos | Valor padrão mensalidade (centavos) | — (default 49000) |
| billing_valor_aplicar_a | todos \| novos | — |
| billing_desconto_percent | Desconto % (0–100) | — |
| billing_desconto_escopo | todos \| ca \| admin_cliente \| especifico | — |
| billing_desconto_tenant_ids | IDs tenants (escopo=especifico) | — |

---

## 12. Arquivos principais

| Componente | Caminho |
|------------|---------|
| Assinatura / billing | `app/models/subscription_billing.py`, `app/models/payment.py`, `app/models/preco_pdv.py`, `app/models/contrato_comercial.py`, `app/models/contrato_aditivo.py`, `app/models/codigo_desconto.py`, `app/models/divulgador.py`, `app/models/divulgador_regra.py`, `app/models/billing_notificacao.py`, `app/models/webhook_event.py` |
| Venda / gateway | `app/models/venda_pagamento.py`, `app/models/payment_provider_config.py`, `app/models/payment_transaction.py`, `app/models/transaction_split.py`, `app/models/split_rule.py`, `app/models/payment_log.py` |
| Guard e tenant pagador | `app/core/subscription_guard.py`, `app/core/scope.py` (resolve_tenant_pagador, get_current_cliente_admin_id) |
| Config billing | `app/core/billing_config.py` |
| Integração MP | `app/integrations/mercadopago.py` (MercadoPagoClient, verify_webhook_signature, create_preference, fetch_payment, validate_token) |
| Serviços | `app/services/billing_service.py`; `app/services/payments/orchestrator.py`, `app/services/payments/providers.py`, `app/services/payments/credentials.py`, `app/services/payments/split_engine.py` |
| APIs | `app/api/v1/billing.py`, `app/api/v1/admin_billing.py`, `app/api/v1/payments.py`, `app/api/v1/venda_pagamentos.py`, `app/api/v1/precos_pdv.py`, `app/api/v1/contratos_comerciais.py`, `app/api/v1/codigos_desconto.py`; `app/api/webhooks_mercadopago.py` |
| Schemas | `app/schemas/billing.py`, `app/schemas/payment.py`, `app/schemas/venda_pagamento.py`, `app/schemas/contrato_comercial.py`, `app/schemas/codigo_desconto.py` |

---

## 13. Checklist de produção

- MP_ACCESS_TOKEN, MP_WEBHOOK_SECRET e APP_URL definidos (configuracoes ou .env).
- Webhook acessível em HTTPS: `{APP_URL}/api/webhooks/mercadopago`. Sempre confirmar pagamento com GET no MP antes de atualizar assinatura.
- Idempotência por **webhook_events** (provider + event_key).
- Trial ao cadastro: ao criar Tenant, chamar `billing_service.create_trial_subscription(db, tenant.id)`.
- Celery Beat rodando: task **billing_daily_job** (notificações + apply_grace_policy).
- Gateway de vendas: estabelecimentos que usam cartão/PIX no PDV precisam de config ativa em **payment_provider_configs** (credenciais Mercado Pago por estabelecimento). Webhook reconcilia **payment_transactions** e sincroniza **venda_pagamentos**.

---

## Apêndice — Origem das informações (fontes)

| Informação | Origem |
|------------|--------|
| Rotas HTML Recebíveis e redirect Pagamentos | `main.py` (linhas 1999–2016): `@app.get("/negocio/recebiveis")`, `@app.get("/negocio/pagamentos")` → redirect para `/negocio/recebiveis`. |
| Template e texto “configuração de recebimento (gateway)” | `app/templates/meu_negocio/pagamentos/index.html`: título Recebíveis, select estabelecimento, tabela de configs, texto “integração de recebimento (gateway)”, “Fase 1, apenas Mercado Pago”. |
| Modal “Nova configuração”, Gateway Mercado Pago, credenciais JSON, POST configs | `app/templates/meu_negocio/pagamentos/index.html`: modal `modalConfigPagamentoCustom`, select `configProviderCode` (option mercadopago), textarea `configCredentials`, `authFetch('/api/v1/payments/configs', { method: 'POST', ... body: { cliente_id, provider_code, credentials, ... })`. |
| APIs de configs e transações (listar configs, listar transações, retry) | `app/templates/meu_negocio/pagamentos/index.html`: `authFetch('/api/v1/payments/configs?estabelecimentoId=' + estabId)`, `authFetch('/api/v1/payments/transactions?estabelecimentoId=...')`, `authFetch('/api/v1/payments/retry/' + uuid, { method: 'POST' })`. |
| Item de menu “Recebíveis” no sidebar | `app/templates/components/sidebar.html`: `<a href="/negocio/recebiveis">` com ícone dollar-sign e condição `negocios.venda:visualizar` ou `negocios.financeiro:visualizar` ou `negocios`. |
| Inclusão do router de payments na API | `main.py`: registro do router `app.api.v1.payments` (prefixo `/api/v1`). |
| Escopo por estabelecimento (CA) e endpoints de configs/process/transactions | `app/api/v1/payments.py`: `get_cliente_scope_dep`, `forbid_cliente_access`, `_allowed_cliente_ids(scope)`, validação de `estabelecimento_id`/`body.cliente_id` contra escopo; Fase 1 só `mercadopago`. |
| Fluxo de processamento (process, orchestrator, provider, transação) | `app/api/v1/payments.py` (POST `/payments/process`) e `app/services/payments/orchestrator.py`: uso de `PaymentProviderConfig` por `cliente_id`, criação de `PaymentTransaction`. |
| Webhook e reconciliação com venda_pagamentos | `app/api/webhooks_mercadopago.py`: reconciliação de `payment_transactions`, `_sync_venda_pagamento_from_transaction`, criação/atualização de `venda_pagamentos`. |
| Uso de `/payments/process` ao finalizar venda (Nova Venda) | `app/templates/meu_negocio/vendas/index.html`: `processarPagamentoGateway(…)` e `authFetch('/api/v1/payments/process', …)`; registro em `venda_pagamentos` após criação da venda. |
| Uso de `/payments/process` no PDV | `app/static/js/pdv.js`: `apiFetch("/api/v1/payments/process", ...)`. |
| Modelo de config por estabelecimento | `app/models/payment_provider_config.py`: `PaymentProviderConfig` com `cliente_id`, `provider_code`, `credentials_encrypted`, etc. |

---

**Última atualização:** 2026-03-09 — Inclusão da seção 2.5 (CA: como recebe o pagamento, onde configura o gateway) e Apêndice com origem das informações (fontes no código). — Anterior: Mapa unificado hierarquia, gateways, distribuição.
