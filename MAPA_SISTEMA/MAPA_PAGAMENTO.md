# MAPA DE PAGAMENTO — PDV Ibix

## Visão Geral

Este documento é a **fonte única de verdade** sobre pagamentos no PDV Ibix: **assinatura SaaS** (trial, billing, bloqueio) e **vendas PDV/loja** (gateway por estabelecimento, Recebíveis, transações). O modelo financeiro marketplace (intermediação/repasse) está em `MAPA_MODELO_PAGAMENTO_MARKETPLACE.md`.

**Modelo (assinatura):** Sem cartão salvo; sem cobrança automática. Cadastro inicia **trial 30 dias**; avisos por e-mail (D-7 a D+15); após **grace_days (15)** sem pagamento o tenant é bloqueado. Confirmação de pagamento sempre via **GET /v1/payments/{id}** (não confiar apenas no redirect).

**Referências cruzadas:** RBAC em `MAPA_RBAC.md`; endpoints em `MAPA_DE_API.md` (§ 17 e billing); arquitetura em `MAPA_DO_SISTEMA.md`; marketplace em `MAPA_MODELO_PAGAMENTO_MARKETPLACE.md`.

---

## 0. Panorama dos 2 fluxos (assinatura + vendas)

| Fluxo | Quem paga | Quem recebe | Gateway / meio | Finalidade |
|-------|-----------|------------|----------------|------------|
| **Assinatura SaaS** | Cliente Administrador (tenant) | Central (SuperAdministrador) | Mercado Pago Checkout Pro (token global billing) | Mensalidade do sistema (trial, ativa, inadimplente, bloqueada) |
| **Vendas (PDV / loja)** | Cliente final na loja | Estabelecimento (CA) ou plataforma (`modo_recebimento`) | Mercado Pago / PagBank / Pagar.me por estabelecimento | Pagamento da venda (cartão, PIX, boleto, etc.) |

- **SuperAdministrador** gerencia cobranças da assinatura (Cobranças Admin).
- **Cliente Administrador (CA)** paga a assinatura do tenant e configura gateway em **Negócios → Recebíveis** por estabelecimento (opcional).

**Distribuição resumida:**

| Camada | Assinatura | Vendas PDV/loja |
|--------|------------|-----------------|
| Tabelas | `subscriptions`, `payments`, `precos_pdv`, `codigos_desconto`, … | `venda_pagamentos`, `payment_provider_configs`, `payment_transactions`, … |
| APIs | `/api/v1/billing/*`, `/api/v1/admin/billing/*` | `/api/v1/payments/*`, `/api/v1/venda-pagamentos` |
| Telas | `/financeiro/assinatura`, `/admin/billing/*` | `/negocio/recebiveis`, PDV |
| Webhook | `POST /api/webhooks/mercadopago` (billing após reconciliar venda) | Mesmo webhook (reconcilia transação + `venda_pagamentos` primeiro) |

Detalhes de CA, gateway e marketplace unificado: § 2.5–2.6 abaixo. *(Conteúdo unificado em 2026-05-21; arquivo legado `mapa_pagamento.md` removido.)*

---

## 1. Modelo de cobrança

| Regra | Descrição |
|-------|-----------|
| Trial | 30 dias a partir do cadastro (subscription.status = trial, period_end = hoje + 30, next_charge_at = period_end, grace_days = 15). |
| D0 | No dia do next_charge_at o status passa de trial para **inadimplente** (sistema continua acessível na carência). |
| Carência | 15 dias após next_charge_at. Durante a carência o usuário ainda acessa; banner e botão "Pagar agora" na página Assinatura. |
| Bloqueio | Se hoje > next_charge_at + grace_days: subscription.status = bloqueada, Tenant.ativo = False (job diário). |
| Pagamento | Sempre manual: usuário clica "Pagar agora" → backend gera preferência Checkout Pro → retorna init_point → abre em nova aba. Meios: Pix, Cartão, Boleto (Checkout Pro oferece todos). |

**Fluxo resumido:** Cadastro → trial 30d → e-mails D-7, D-3, D-1, D0 → D0 vira inadimplente → e-mails D+1, D+7, D+14, D+15 → se pagar: webhook confirma → ativa/renova +30d; se não pagar até D+15 → bloqueio.

---

## 2. RBAC e telas

### 2.1 Super Administrador

- **Menu "Cobranças (Admin)"** (somente SA, sidebar): link para `/admin/billing/tenants`. Lista de tenants (status, vencimento, dias em atraso), gerar cobrança/copiar link, ver pagamentos, bloquear/desbloquear. Na página tenants: botões **Valor e descontos** (`/admin/billing/preco`), **Códigos de desconto** (`/admin/billing/codigos-desconto`), **Config** (MP e APP_URL). Em **Códigos de desconto** (2026-03-02): Novo Divulgador e Novo Código (Super Admin); ao criar código, o select **Representante (Administrador)** lista os usuários com função Administrador; o código fica vinculado ao representante escolhido (divulgador encontrado ou criado automaticamente).
- **Rotas HTML:** `GET /admin/billing/tenants`, `GET /admin/billing/tenant/<tenant_id>`, `GET /admin/billing/config`, **`GET /admin/billing/preco`**, **`GET /admin/billing/precos-pdv`**, **`GET /admin/billing/codigos-desconto`**. Templates em `app/templates/admin/billing_tenants.html`, `billing_tenant_detail.html`, `billing_config.html`, **`billing_preco.html`**, **`precos_pdv.html`**, **`codigos_desconto.html`**.
- **Guards:** Verificação `user.role.nome == "Superadministrador"` em todas as rotas HTML `/admin/billing/*`; API usa `require_superadmin()`.
- **Status gateway:** Na lista de tenants, o badge "Mercado Pago: Conectado" só aparece após **validação real** do token (GET `/api/v1/admin/billing/config/validate` chama a API do MP). "Token inválido ou sem permissão" se o token for rejeitado.

### 2.2 Cliente Administrador e Subcliente

- **Menu Assinatura:** status da assinatura, próximo vencimento, dias de carência, último pagamento, botão **Pagar agora**, histórico de pagamentos (somente leitura).
- **Rota HTML:** `GET /financeiro/assinatura` (template `app/templates/financeiro/assinatura.html`).
- **Não têm:** criação/edição de plano, alterar preço, configurar gateway, bloquear/desbloquear, reprocessar webhook.

### 2.3 Quando assinatura está bloqueada

- **SubscriptionGuard:** rotas fora da **allowlist** retornam 403 (API) ou redirecionam para `/financeiro/assinatura` (HTML).
- **Sidebar:** exibe **apenas** o item "Assinatura" (e brand); demais itens do menu ficam ocultos. Variável de contexto: `subscription_blocked` (calculada em `get_template_context` via `is_subscription_blocked(db, user)`).

### 2.4 Quem paga o quê (resolve_tenant_pagador)

- **Cliente Administrador:** tenant_id = `current_user.tenant_id`.
- **Subcliente / Técnico / Contador:** tenant_id = tenant do CA ao qual estão vinculados (`get_current_cliente_admin_id` → usuario_id do CA → `usuarios.tenant_id` desse CA).
- **Superadministrador / Administrador:** não aplica bloqueio por assinatura (sem tenant de cobrança).
- **Implementação:** `app/core/scope.py` — `resolve_tenant_pagador(db, user_id, role_nome)` retorna `tenant_id` ou None.

### 2.5 Gateway de vendas (Fase 3.3 – pagamento por estabelecimento)

- Configuração em **`payment_provider_configs`** por estabelecimento (cliente_id). **Restrito por tenant do CA:** apenas estabelecimentos no escopo do usuário (ClienteScope.allowed_ids) podem ter configs listadas/criadas; **cada CA configura seu próprio gateway se quiser** (opcional por estabelecimento).
- **Gateways permitidos:** `mercadopago`, `pagbank`, `pagarme`. Sem split: valor integral vai para a conta do CA.
- **PagBank:** OAuth Connect (redirect). **Pagar.me:** Secret Key (HTTP Basic). **Mercado Pago:** Access Token (JSON).
- Ver MAPA_DE_REGRAS § 14.

#### 2.5.1 Modo de Recebimento (empresa.modo_recebimento)

Cada **Empresa Fiscal** possui campo `modo_recebimento` (definido pelo **SuperAdmin** em Fiscal > Empresa):

- **`direto`** — CA recebe o valor das vendas diretamente na conta do gateway configurado em Recebíveis (OAuth/Key).
- **`plataforma`** (default) — A plataforma recebe o valor total via conta billing Mercado Pago. O SuperAdmin registra repasses manuais em **Negócios > Financeiro**.

O **PaymentOrchestrator** (vendas PDV) e o **checkout da vitrine** (loja) consultam `empresa.modo_recebimento` para decidir qual credencial usar:
- modo=`direto`: usa `PaymentProviderConfig` do CA (Recebíveis).
- modo=`plataforma`: usa `billing_config.get_mp_access_token()` (conta MP da plataforma).

**Checkout da vitrine (loja):** O serviço `create_checkout_for_pedido` (`app/services/payments/checkout_marketplace_service.py`) aplica a mesma regra: se a empresa fiscal do dono da loja (CA) estiver em modo `plataforma`, usa credenciais da plataforma; se `direto`, usa a config do CA em Recebíveis. Função interna: `_resolve_provider_and_credentials`.

Cada `PaymentTransaction` grava `modo_recebimento` para rastreabilidade.

#### 2.5.2 Taxas da Plataforma

Quando `modo_recebimento = 'plataforma'`, o SuperAdmin pode configurar na Empresa Fiscal:
- `taxa_plataforma_percentual` — percentual sobre vendas (ex: 5.00 = 5%).
- `taxa_plataforma_valor_fixo` — valor fixo por transação (ex: R$ 2,50).

Essas taxas são aplicadas no cálculo do saldo pendente de repasse.

#### 2.5.3 Repasses (tabela `repasses`)

Modelo `Repasse`: registro de transferência da plataforma para o CA. Campos: `cliente_id`, `valor_bruto`, `valor_taxa`, `valor_liquido`, `periodo_inicio`, `periodo_fim`, `status` (pendente/repassado/cancelado), `data_repasse`, `comprovante`, `observacao`, `usuario_id`.

API em `/api/v1/negocio/financeiro/repasses/` (SuperAdmin only):
- `GET /resumo` — saldos por CA (vendas bruto, taxa, repassado, pendente).
- `GET /extrato` — lista de repasses com filtro.
- `POST /` — criar repasse manual.
- `PUT /{id}` — atualizar status/comprovante.
- `GET /taxas` — taxas configuradas por empresa.

### 2.6 CA: como recebe o pagamento e onde configura o gateway

#### Onde o dinheiro cai

O valor vai para a **conta do gateway** (Mercado Pago, PagBank ou Pagar.me) cujas credenciais estão na **configuração de gateway do estabelecimento**. Sem split: o valor integral cai na conta do CA. Essa config é por estabelecimento (por `cliente_id`), e o CA só vê/edita estabelecimentos do seu escopo.

#### Fluxo no sistema

1. Na **venda** (PDV ou Nova Venda), ao finalizar com forma cartão/PIX (etc.), o front chama **POST** `/api/v1/payments/process` (estabelecimento, venda, valor, método, idempotency_key).
2. O backend usa a config ativa do estabelecimento em **payment_provider_configs**, chama o provedor configurado (MP, PagBank ou Pagar.me), cria/atualiza **payment_transactions**. Webhooks em **POST** `/api/v1/payments/webhook/{provider_code}` atualizam status e reconciliam.
3. O CA “recebe” no sistema quando a transação fica **paid/authorized** e o **venda_pagamento** correspondente fica **confirmado**; o dinheiro de fato cai na conta do gateway ligada às credenciais/OAuth da config daquele estabelecimento.

#### Onde o CA acompanha

- **Recebíveis** (`/negocio/recebiveis`): lista de **configurações de gateway** por estabelecimento e lista de **transações** via **GET** `/api/v1/payments/transactions`. Filtros: Todas, Pagas, Pendentes e falhas. Transações pagas visíveis; coluna Referência (numero_pedido ou Venda #id), Pago em. **Comprovante:** botão em transações pagas — fetch para **GET** `/api/v1/payments/transactions/{uuid}/comprovante` (retorna HTML imprimível). **Verificar status:** botão em pendentes chama **POST** `/api/v1/payments/reconcile/{uuid}`.
- **Vendas:** cada venda tem seus pagamentos fracionados em **venda_pagamentos** (forma, valor, status, id_externo), acessíveis pela tela de vendas e por **GET/POST** `/api/v1/venda-pagamentos/?venda_id=...`.

**Resumo:** o CA recebe o pagamento na conta do gateway (MP, PagBank ou Pagar.me) cujas credenciais/OAuth estão na config do estabelecimento; no sistema, isso aparece como transações em **Recebíveis** e como **venda_pagamentos** nas vendas.

**Marketplace — checkout unificado (várias lojas, um pagamento) e Recebíveis — atualização 2026-05-15:** Quando o consumidor paga um único PIX/cobrança que cobre **vários pedidos marketplace** (`PaymentTransaction.checkout_session_id` preenchido), a linha persistida pode ter `cliente_id`/`pedido_id` do pedido âncora. **Listagem Recebíveis** (`GET /api/v1/payments/transactions?estabelecimentoId=`) e checagens de escopo relacionadas usam `app/services/payments/marketplace_unified_payment_scope.py`: todo CA que tenha **`pedidos_marketplace.tenant_id`** igual ao seu aparece como participante e vê **`amount`** e referência de pedido **proporcionais à sua parte** na sessão. No webhook de confirmação, **`BillingUsageEvent` / `record_payment_billing`** grava **`cliente_id`** por **`pedido.tenant_id`** (evento por pedido). SuperAdmin — **repasses**: `GET /negocio/financeiro/repasses/transacoes` (e derivados resumo/sugestão por `cliente_id`) aplicam o mesmo rateio ao filtrar transações modo plataforma. Ver `MAPA_DO_SISTEMA.md` § 12 (subseção «Checkout unificado…») e `MAPA_DE_API.md` § Pagamentos / Repasses.

#### Onde o CA configura o gateway

| Aspecto | Detalhe |
|--------|---------|
| **Menu** | Negócios → **Recebíveis** (sidebar: ícone dollar-sign, link Recebíveis). |
| **URL** | `/negocio/recebiveis` (e `/negocio/pagamentos` redireciona para ela). |
| **Tela** | Seleção de **estabelecimento (cliente)** no topo. Tabela de configurações do estabelecimento: listagem via **GET** `/api/v1/payments/configs?estabelecimentoId=<id>`. Botão **“Nova configuração”** abre o modal de nova config. No modal: Estabelecimento, Gateway (Mercado Pago / PagBank / Pagar.me), campos dinó “Mercado Pago”), Credenciais (JSON) (opcional), Ativo, Padrão, Modo teste. Para PagBank: botão OAuth. Para Pagar.me: campo Secret Key; ao salvar chama **POST** `/api/v1/payments/configs` com `cliente_id`, `provider_code`, `credentials`, etc. |
| **Permissão** | Usuário precisa de alguma permissão de negócios (`negocios.venda:visualizar` ou `negocios.financeiro:visualizar` ou `negocios`). |
| **Escopo** | Só aparecem estabelecimentos do **escopo do CA** (`ClienteScope.allowed_ids`); a API de configs valida `estabelecimento_id` / `cliente_id` contra esse escopo. |
| **Self-service lojas** | Chave `payment_lojas_gateway_self_service` (Admin → Billing → Config → **Liberado para lojas**). **true** (default se ausente): CA e Administrador podem POST/PATCH configs e OAuth PagBank. **false**: só **Superadministrador** muta; API retorna 403 com mensagem explícita; UI Recebíveis esconde Nova/Editar e exibe alerta (`GET /payments/modo-recebimento` → `gateway_configuracao_permitida`). |

Ou seja: o CA configura o gateway em **Negócios → Recebíveis** quando **Liberado para lojas** estiver ativo, escolhendo o estabelecimento e conectando via OAuth (PagBank), informando Secret Key (Pagar.me) ou Access Token JSON (Mercado Pago) com credenciais e opções ativo/padrão/teste.

---

## 3. Banco de dados

| Tabela | Descrição |
|-------|-----------|
| **subscriptions** | Assinatura por tenant: tenant_id, plano_codigo, valor_mensal_centavos, **qtd_pdvs_contratados** (default 1), status (trial, ativa, inadimplente, bloqueada, cancelada), grace_days, period_start, period_end, next_charge_at, last_paid_at, blocked_at, mp_preference_id, last_payer_user_id. Modelo: `app/models/subscription_billing.py`. |
| **precos_pdv** | Preços de licença PDV: valor_base_centavos (R$ 170 default), valor_pdv_adicional_centavos (R$ 70 default), vigencia_inicio, ativo. Fórmula: `valor_mensal = base + (qtd - 1) × adicional`. Valores nunca hardcoded. Modelo: `app/models/preco_pdv.py`. Migração: `nn33pp469v9`. |
| **contrato_comercial** | Contrato de assinatura SaaS por tenant: tenant_id, vigencia_inicio, vigencia_fim, qtd_pdvs_contratados, valor_mensal_centavos, status (ativo, encerrado, cancelado). Modelo: `app/models/contrato_comercial.py`. |
| **contrato_aditivos** | Alteração formal do contrato: contrato_id, data_aditivo, qtd_pdvs_anterior, qtd_pdvs_nova, valor_anterior_centavos, valor_novo_centavos, motivo. Modelo: `app/models/contrato_aditivo.py`. |
| **codigos_desconto** | Códigos de promoção: codigo (unique), tipo_promocao, desconto_primeira_parcela_percent, desconto_mensalidade_percent, meses_desconto, ativo, divulgador_id (FK divulgadores). Modelo: `app/models/codigo_desconto.py`. |
| **divulgadores** | Pessoas divulgadoras/parceiros: nome, cpf_cnpj, email, ativo, usuario_id (vínculo opcional). Modelo: `app/models/divulgador.py`. |
| **divulgador_regras** | Regras de comissão: divulgador_id, percentual_plano_ativo, recebe_primeira_parcela, percentual_comissao. Modelo: `app/models/divulgador_regra.py`. |
| **payments** | Rastreio de pagamentos MP: subscription_id (FK subscriptions.id), mp_payment_id (único), status, amount_centavos, paid_at, external_reference, payer_user_id (quem clicou "Pagar agora"), raw_json. Modelo: `app/models/payment.py`. |
| **webhook_events** | Idempotência do webhook MP: provider, event_key (ex.: payment:{id}), received_at, processed_at, raw_json. UNIQUE(provider, event_key). Modelo: `app/models/webhook_event.py`. |
| **billing_notificacoes** | Anti-spam de e-mails: tenant_id, tipo (trial_d7, trial_d3, …, pastdue_d15), sent_at, canal (email/whatsapp). UNIQUE(tenant_id, tipo). Modelo: `app/models/billing_notificacao.py`. |
| **billing_events** | Webhook genérico (idempotência por webhook_id). Já existente; ver `MAPA_DE_API.md` § 17. |

**Migrações:** `y56aa458n4x0_add_subscriptions_billing.py` (subscriptions); `z67bb569o5y1_add_payments_webhook_events_billing_notificacoes.py` (payments, webhook_events, billing_notificacoes); **`nn33pp469v9_fase2_precos_contrato_desconto.py`** (precos_pdv, contrato_comercial, contrato_aditivos, divulgadores, divulgador_regras, codigos_desconto + seed); **`oo44qq570w0_add_qtd_pdvs_subscriptions.py`** (subscriptions.qtd_pdvs_contratados).

**Bloqueio:** O guard usa **Tenant.ativo**: quando subscription fica bloqueada, `Tenant.ativo = False`. `is_subscription_blocked(db, user)` considera bloqueado se o tenant resolvido (via `resolve_tenant_pagador`) tiver `ativo = False`.

---

## 4. API (endpoints)

**Routers:** Cliente/Admin em `/api/v1` (prefix); billing em `app/api/v1/billing.py` (prefix `/billing`); admin billing em `app/api/v1/admin_billing.py` (prefix `/admin/billing`). Webhook MP em **POST /api/webhooks/mercadopago** (router em `app/api/webhooks_mercadopago.py`, prefix `/api/webhooks`).

### 4.1 Cliente (CA / Subcliente)

| Método | Rota completa | Descrição |
|--------|----------------|-----------|
| GET | `/api/v1/billing/my-subscription` | Status da assinatura. Retorna **server_today**, status, period_end, next_charge_at, grace_days, **trial_days_left**, **grace_days_left**, **is_in_trial**, **is_past_due**, **is_blocked** (todos calculados no backend). |
| **GET** | **`/api/v1/billing/meus-limites`** | **Limites de PDVs: max_pdvs, pdvs_usados, pdvs_disponiveis, pode_criar_pdv, valor_mensal_centavos, valor_exibicao.** Front consome para badge e botão. |
| POST | `/api/v1/billing/pay-now` | Gera preferência Checkout Pro; retorna init_point e preference_id. Front abre init_point em nova aba. |
| GET | `/api/v1/billing/my-payments?limit=50` | Lista pagamentos da assinatura (somente leitura). |

### 4.2 Super Admin

| Método | Rota completa | Descrição |
|--------|----------------|-----------|
| GET | `/api/v1/admin/billing/tenants?status=&q=&page=&per_page=&apenas_com_ca=` | Lista tenants com status assinatura, vencimento, dias em atraso. **apenas_com_ca=true:** só tenants que possuem pelo menos um usuário com role "Cliente Administrador" (apenas C; exclui CF). Usado no select "Específico" da página Valor e descontos (per_page até 10000). Dependency: require_superadmin(). |
| GET | `/api/v1/admin/billing/tenant/{tenant_id}` | Detalhe: assinatura, pagamentos, ações. |
| POST | `/api/v1/admin/billing/tenant/{tenant_id}/create-charge` | Gera preferência e retorna init_point (copiar link). |
| POST | `/api/v1/admin/billing/tenant/{tenant_id}/block` | Seta subscription.status = bloqueada, Tenant.ativo = False. |
| POST | `/api/v1/admin/billing/tenant/{tenant_id}/unblock` | Seta Tenant.ativo = True, subscription.status = inadimplente se estava bloqueada. |
| GET | `/api/v1/admin/billing/config` | Config gateway (mp_configured, app_url; sem expor segredos). |
| POST | `/api/v1/admin/billing/config` | Salva Access Token, Webhook Secret e APP_URL na tabela **configuracoes** (chaves billing_*). |
| GET | `/api/v1/admin/billing/config/validate` | **Validação real do token:** chama API MP (GET api.mercadolibre.com/users/me). Retorna mp_valid, mp_message. Usado para o badge "Conectado" na lista de tenants. |
| GET | `/api/v1/admin/billing/preco` | Valor mensal (centavos), valor_aplicar_a (todos\|novos), desconto_percent, desconto_escopo (todos\|ca\|admin_cliente\|especifico), desconto_tenant_ids. |
| POST | `/api/v1/admin/billing/preco` | Salva valor mensal e regras de desconto (persistido em **configuracoes**). |
| POST | `/api/v1/admin/billing/preco/aplicar-valor-todos` | Atualiza **valor_mensal_centavos** de todas as assinaturas. Body: `respeitar_codigos_promocionais` (boolean, default true). **true:** assinaturas com codigo_desconto_id mantêm o desconto sobre o novo base; **false:** todas recebem o mesmo valor (ignora códigos). Contrato comercial ativo sempre prevalece. |

### 4.2b Preços PDV (Super Admin)

| Método | Rota completa | Descrição |
|--------|----------------|-----------|
| GET | `/api/v1/admin/precos-pdv/` | Lista todos os preços (histórico). Require: SuperAdmin. |
| GET | `/api/v1/admin/precos-pdv/vigente` | Preço vigente (ativo, mais recente). |
| POST | `/api/v1/admin/precos-pdv/` | Criar novo preço (valor_base_centavos, valor_pdv_adicional_centavos, vigencia_inicio). |
| PATCH | `/api/v1/admin/precos-pdv/{id}` | Atualizar preço (valor_base, adicional, ativo). |

### 4.2c Contratos Comerciais (Super Admin / Administrador)

| Método | Rota completa | Descrição |
|--------|----------------|-----------|
| GET | `/api/v1/contratos-comerciais/?tenant_id=&status=` | Lista contratos. |
| GET | `/api/v1/contratos-comerciais/{id}` | Detalhe do contrato. |
| POST | `/api/v1/contratos-comerciais/` | Criar contrato (tenant_id, vigencia_inicio, qtd_pdvs_contratados). Valor calculado automaticamente com precos_pdv vigente. Sincroniza subscriptions.qtd_pdvs_contratados. |
| GET | `/api/v1/contratos-comerciais/{id}/aditivos` | Lista aditivos do contrato. |
| POST | `/api/v1/contratos-comerciais/{id}/aditivos` | Criar aditivo (qtd_pdvs_nova, motivo). Atualiza contrato e subscription. |

### 4.2d Códigos de Desconto e Divulgadores (Super Admin / Administrador)

| Método | Rota completa | Descrição |
|--------|----------------|-----------|
| GET | `/api/v1/divulgadores?ativo=` | Lista divulgadores. |
| POST | `/api/v1/divulgadores` | Criar divulgador (nome, cpf_cnpj, email). |
| PATCH | `/api/v1/divulgadores/{id}` | Atualizar divulgador. |
| GET | `/api/v1/divulgadores/{id}/regras` | Regras de comissão do divulgador. |
| POST | `/api/v1/divulgadores/{id}/regras` | Criar regra de comissão. |
| GET | `/api/v1/codigos-desconto?ativo=` | Lista códigos. |
| GET | `/api/v1/codigos-desconto/{id}` | Detalhe do código. |
| POST | `/api/v1/codigos-desconto` | Criar código. Aceita `representante_usuario_id` (id do usuário Administrador; backend encontra ou cria divulgador) ou `divulgador_id`; pelo menos um obrigatório. Demais: codigo, tipo_promocao, descontos. |
| PATCH | `/api/v1/codigos-desconto/{id}` | Atualizar código. |
| **GET** | **`/api/v1/codigos-desconto/validar/{codigo}`** | **Público (sem auth).** Verifica se código é válido e ativo. Usado no cadastro/checkout. |

### 4.3 Webhook Mercado Pago (configurar notificações de pagamento)

**Domínio externo de produção (Ibix):** `https://www.ibix.com.br` — é o host público oficial da vitrine e da API em produção. URL completa a cadastrar no Mercado Pago (notificações / webhook):  
`https://www.ibix.com.br/api/webhooks/mercadopago?source_news=webhooks`  
(Em outros ambientes, troque o host; o path e a query `source_news=webhooks` permanecem.)

- **POST** `/api/webhooks/mercadopago` — Sem autenticação JWT. Validação por headers **x-signature** e **x-request-id** (HMAC). **POST** `/api/webhooks/payments/mercadopago` delega para o mesmo handler. Idempotência por `webhook_events` (event_key = payment:{id}). Sempre confirmar status via **GET https://api.mercadopago.com/v1/payments/{id}** antes de atualizar assinatura/tenant. Resposta 200 dentro do prazo (MP espera até 22 s). Secrets candidatos: `app/core/mp_webhook_secrets.py` → `list_mp_webhook_secret_candidates` (global Billing + por estabelecimento).

#### 4.3.1 Alinhamento com a doc. “Configurar notificações de pagamento” — conferido

| Requisito (doc. MP) | No sistema |
|---------------------|------------|
| **URL de notificação** | Enviada na preferência como `notification_url` (`{APP_URL}/api/webhooks/mercadopago?source_news=webhooks` recomendado) e/ou configurável em Suas integrações > Webhooks. **Produção Ibix:** `https://www.ibix.com.br/api/webhooks/mercadopago?source_news=webhooks`. Alinhar `APP_URL` / `SEO_PUBLIC_BASE_URL` no `.env` a esse domínio. |
| **Evento Pagamentos** | Rota aceita POST com body `type: "payment"` e `data.id`; ignora outros tipos retornando 200. |
| **Validar origem (x-signature)** | `app/integrations/mercadopago.py`: `parse_x_signature` (ts, v1), manifest `id:{data.id};request-id:{x-request-id};ts:{ts};`, HMAC-SHA256 em hex; `verify_webhook_signature` tenta cada secret retornado por `list_mp_webhook_secret_candidates` (`app/core/mp_webhook_secrets.py`): (1) `get_mp_webhook_secret` → **billing_mp_webhook_secret** ou env **MP_WEBHOOK_SECRET**; (2) por `payment_provider_configs` Mercado Pago ativo: coluna **webhook_secret_encrypted** e JSON **webhook_secret** / **WEBHOOK_SECRET** / **mp_webhook_secret**. Credenciais teste vs produção no MP têm secrets diferentes. |
| **Resposta 200/201** | Webhook retorna `{"status": "ok"}` (HTTP 200). Em caso de exceção no processamento, ainda responde 200 para evitar reenvio em loop. |
| **Após receber: GET payment por ID** | `process_payment_webhook` chama `client.fetch_payment(payment_id)` (GET /v1/payments/{id}), depois atualiza Payment, Subscription e Tenant.ativo. |
| **Idempotência** | Tabela **webhook_events** com `event_key = payment:{id}`; evento já processado não é reprocessado. |

**Observação:** Pagamentos de **teste** (credenciais de teste) não disparam notificação real; para testar recepção use **Simular** em Suas integrações > Webhooks, ou um pagamento em produção.

**Checkout vitrine — erro `Mercado Pago recusou: HTTP 403` ao criar preferência:** em geral **credencial**, não “conexão”. O backend valida o token com **GET** `https://api.mercadolibre.com/users/me` (doc. MP) antes do POST da preferência; se falhar, o log mostra o motivo. Conferir: (1) **Access Token** de produção (`APP_USR-...`) em Admin Billing (`billing_mp_access_token`) ou `MP_ACCESS_TOKEN`, válido e da mesma aplicação MP do painel; (2) não misturar token de **teste** com conta **produção**; (3) token expirado/revogado — gerar novo em Suas integrações > Credenciais. Respostas 403 com **corpo vazio**: o log inclui `x-request-id` (se vier no header) e orientação; ainda assim quase sempre é token ou ambiente incorreto.

### 4.4 Valor mensal e descontos (Super Admin)

- **Página:** `/admin/billing/preco` — botão "Valor e descontos" na tela Cobranças > Tenants.
- **Valor mensal (R$):** Valor padrão da mensalidade. Persistido em **configuracoes** (`billing_valor_mensal_centavos`). Fallback 49000 (R$ 490,00).
- **Aplicar valor a:** `todos` (todos os assinantes) ou `novos` (apenas novas assinaturas). Chave `billing_valor_aplicar_a`. Botão **"Aplicar valor a todas as assinaturas atuais"** chama POST `/admin/billing/preco/aplicar-valor-todos` com opção escolhida: **Respeitar códigos promocionais** (default) — assinaturas com `codigo_desconto_id` mantêm o desconto sobre o novo valor base; **Substituir em todas (ignorar códigos)** — todas recebem o mesmo valor configurado (com desconto por escopo). Contrato comercial ativo sempre prevalece.
- **Desconto (%):** 0–100. Chave `billing_desconto_percent`. Valor cobrado = valor_mensal × (1 − desconto/100); **desconto 100%** ⇒ mensalidade efetiva **0 centavos** (não é mais forçado `max(1, …)`).
- **Isenção real:** Se `get_valor_centavos_para_tenant` for **0** (desconto admin no escopo, ou **contrato comercial** com valor mensal zero), o sistema **não** aplica bloqueio por carência nesse tenant; trial que encerra **não** vira inadimplente; **inadimplente** com valor zero é renovado em cortesia (+30 dias, como após pagamento); **não** há e-mails pastdue; `create_checkout_preference` / `POST /billing/pay-now` renovam sem Mercado Pago. Contrato comercial ativo com valor > 0 continua prevalecendo sobre o desconto admin.
- **Desconto para (escopo):** `todos` | `ca` (Cliente Administrador: tenant com usuário role "Cliente Administrador") | `admin_cliente` (tenant com usuário role "Administrador de Cliente") | `especifico` (lista de tenant_id em `billing_desconto_tenant_ids`). No **especifico**, o select "Tenants com desconto" é preenchido via GET `/api/v1/admin/billing/tenants?apenas_com_ca=true&per_page=10000` — lista apenas tenants que possuem pelo menos um usuário com role "Cliente Administrador" (apenas C; não lista CF).
- **Lógica no serviço:** `billing_service._valor_centavos_para_tenant(db, tenant_id)` usa `get_valor_mensal_centavos(db)` e, se `_tenant_tem_desconto(db, tenant_id)` (conforme escopo), aplica o percentual. Usado em `create_trial_subscription`, `create_checkout_preference` e ao aplicar valor a todos (com ou sem respeito a codigo_desconto_id conforme body).
- **Configuração:** `app/core/billing_config.py` — getters `get_valor_mensal_centavos`, `get_valor_aplicar_a`, `get_desconto_percent`, `get_desconto_escopo`, `get_desconto_tenant_ids`.

### 4.5 Páginas de retorno (Checkout Pro)

- **GET** `/billing/success`, `/billing/failure`, `/billing/pending` — Redirecionam para `/financeiro/assinatura` (back_urls do MP). Implementação em `main.py` (linhas ~906–921).

#### 4.5.1 Configurar URLs de retorno (doc. Mercado Pago) — conferido

Conforme a documentação **Configurar URLs de retorno** do MP:

| Requisito / Atributo | No sistema |
|----------------------|------------|
| **back_urls** na preferência (backend) | Enviados em `create_checkout_preference`: `success`, `failure`, `pending` com base em APP_URL (`{APP_URL}/billing/success`, `/billing/failure`, `/billing/pending`). |
| **auto_return** | `"approved"` — comprador é redirecionado automaticamente ao site quando o pagamento é aprovado (até 40 s). |
| Três cenários | success (aprovado), failure (rejeitado), pending (pendente, ex. boleto). |
| Rotas que recebem o retorno | GET `/billing/success`, `/billing/failure`, `/billing/pending`; hoje redirecionam para `/financeiro/assinatura` sem repassar query params. |

**Parâmetros que o MP envia na resposta (GET):** `payment_id`, `status`, `external_reference`, `collection_id`, `collection_status`, `payment_type`, `merchant_order_id`, `preference_id`, `site_id`, etc. Podem ser repassados para `/financeiro/assinatura` (ex.: `?payment=approved`) para exibir mensagem contextual na página de assinatura; a confirmação definitiva do pagamento é feita via **webhook** e **GET /v1/payments/{id}**, não apenas pelo redirect.

#### 4.5.2 Modelo web vs. integração para aplicações móveis (doc. MP)

O PDV Ibix usa hoje o **Checkout Pro em modelo web**: o backend gera a preferência e devolve o **init_point**; o front (Jinja2/JS) abre esse link em nova aba (`window.open(init_point, '_blank')`). O usuário paga na página hospedada do Mercado Pago e volta às **back_urls** (success/failure/pending) do nosso domínio. Esse fluxo funciona também em **navegador mobile** (acesso ao site pelo celular): a mesma tela de assinatura e o mesmo init_point são usados; a página do MP é responsiva.

A documentação **Integração para aplicações móveis** do MP aplica-se a **aplicativos nativos** (Flutter, React Native CLI, React Native Expo, Java/Kotlin, Swift). Nesse modelo, o frontend é o app nativo com SDK do MP; as **back_urls** devem ser **deep links** para reabrir o app após o pagamento. O backend (criação de preferência, webhook) permanece igual; só o cliente muda (app nativo em vez de navegador).

| Aspecto | Situação no sistema |
|--------|----------------------|
| **Modelo atual (billing assinatura)** | Web: init_point aberto no navegador. Compatível com acesso mobile via browser. |
| **App nativo (Flutter, React Native, etc.)** | Não implementado. Se houver no futuro, usar a doc. "Integração para aplicações móveis" e configurar back_urls como deep links. |
| **WebView** | Não utilizado. O aviso de descontinuação do MP (WebView com login em browser embutido) não se aplica ao nosso fluxo (redirecionamento para a página do MP, não WebView). |

Referência doc. MP: Integração para aplicações móveis — Flutter, React Native CLI, React Native Expo, Java/Kotlin, Swift.

#### 4.5.3 Frontend: SDK/brick vs. redirect (init_point) — concluído com modelo redirect

A documentação **Adicionar o SDK ao frontend e inicializar o checkout** descreve o uso do **MercadoPago.js** (CDN ou React): incluir o script, configurar a Public Key, passar o **preferenceId** e renderizar o componente **wallet** (botão de pagamento do MP) em um container. O comprador clica no botão e é enviado ao ambiente de compra do MP.

No PDV Ibix o fluxo de assinatura usa o **modelo por redirect**, não o SDK/brick no front:

| Doc (SDK + brick) | Nosso modelo (redirect) |
|-------------------|---------------------------|
| Incluir `<script src="https://sdk.mercadopago.com/js/v2"></script>` | Não utilizamos o SDK no front. |
| Inicializar `new MercadoPago(publicKey)`, criar brick "wallet" com `preferenceId` | Não utilizamos. |
| Container `walletBrick_container` para o botão do MP | Botão próprio "Pagar agora" no template. |
| Backend devolve **preferenceId** → front passa ao brick | Backend devolve **init_point** (URL do Checkout Pro). Front faz `window.open(init_point, '_blank')`. |

**Conclusão:** A etapa de “configurar o frontend para completar a experiência de pagamento” está **concluída** no nosso caso: o usuário clica em "Pagar agora", o front chama POST `/api/v1/billing/pay-now`, recebe o **init_point**, abre essa URL em nova aba e o comprador conclui o pagamento no ambiente do Mercado Pago. Não é necessário carregar o SDK nem renderizar o brick quando se usa o **init_point** (redirecionamento direto para a página do Checkout Pro). Se no futuro for desejado o botão oficial do MP na página (brick), será preciso incluir o SDK, a Public Key e o container, e passar o `preferenceId` retornado pelo nosso backend.

---

## 5. SubscriptionGuard e allowlist

**Arquivo:** `app/core/subscription_guard.py`.

- **Allowlist (rotas acessíveis quando bloqueado):** `/financeiro/assinatura`, `/api/v1/billing/my-subscription`, `/api/v1/billing/pay-now`, `/billing/success`, `/billing/failure`, `/billing/pending`, `/auth/login`, `/logout`, `/static`.
- **Dependency:** `subscription_guard(request, db, current_user)` — para rotas API: se tenant bloqueado e path **fora** da allowlist → HTTP 403.
- **Middleware HTML:** Em `main.py`, middleware `subscription_block_redirect` roda após `add_user_to_request`; se path não está na allowlist (e não é `/static` nem `/api/`) e usuário tem tenant bloqueado → **RedirectResponse** para `/financeiro/assinatura`.
- **Função:** `is_subscription_blocked(db, user)` — retorna True se o tenant resolvido (resolve_tenant_pagador) tiver `Tenant.ativo = False`.

---

## 6. Front (Jinja2 + JS)

### 6.1 Regra de dias no front

O front **não calcula datas** (evitar fuso/relógio). Exibe apenas o que a API devolve.

- **GET my-subscription** retorna: server_today, trial_days_left, grace_days_left, is_in_trial, is_past_due, is_blocked.
- **Mensagens:** Se is_in_trial → "Faltam X dias do teste". Se is_past_due e não bloqueado → "Você está no período de carência: X dias". Se is_blocked → "Conta bloqueada. Pagar para reativar."

### 6.2 Página Assinatura

- **Rota:** GET `/financeiro/assinatura`. Auth: `check_auth_for_html`.
- **Template:** `app/templates/financeiro/assinatura.html` (estende base.html). Cards: status (carregado via GET my-subscription), botão "Pagar agora" (POST pay-now → window.open(init_point)), histórico (GET my-payments). Alerta vermelho se `subscription_blocked` (contexto).

### 6.3 Sidebar (menu quando bloqueado)

- **Arquivo:** `app/templates/components/sidebar.html`.
- Se **subscription_blocked | default(false)** → exibe apenas o item "Assinatura".
- Caso contrário: Subcliente tem item "Assinatura" no Portal; Cliente Administrador, Técnico e Contador têm item "Assinatura" em Principal.

---

## 7. E-mails automáticos

- **Job diário** (1x/dia, ex.: 03:00) processa notificações.
- **Anti-spam:** Tabela **billing_notificacoes** (tenant_id, tipo, sent_at, canal). UNIQUE(tenant_id, tipo). O job só envia se **não** existir registro para aquele (tenant_id, tipo).
- **Tipos (ex.):** trial_d7, trial_d3, trial_d1, trial_d0; pastdue_d1, pastdue_d7, pastdue_d14, pastdue_d15.
- **Conteúdo:** Assunto objetivo; 3 linhas de texto; link "Pagar agora" (para `/financeiro/assinatura` ou init_point gerado na hora); assinatura PDV Ibix.
- **D0:** Se a mensalidade efetiva for **zero**, o job renova em cortesia (`ativa`, próximo ciclo em +30 dias); caso contrário, além do e-mail trial_d0, o job seta subscription.status = inadimplente.

---

## 8. Job diário (Celery)

- **Task principal:** `app.worker.tasks.billing_daily_job` — chama `apply_grace_policy(db)` e `process_billing_notifications(db)`.
- **apply_grace_policy:** Para subscriptions com status ativa ou inadimplente e `hoje > next_charge_at + grace_days`: seta status = bloqueada, blocked_at = now, **Tenant.ativo = False**, exceto quando **get_valor_centavos_para_tenant == 0** (isenção). Retorna quantidade alterada.
- **process_billing_notifications:** Retorna `(notifications_sent, precisa_invalidar_cache)`. Envia e-mails trial_d7… e pastdue… apenas quando há cobrança efetiva (**valor mensal > 0**). No D0 do trial, mensalidade zero ⇒ cortesia (sem inadimplente, sem e-mail de cobrança). Para **inadimplente** com mensalidade zero, renova cortesia e não envia pastdue. Usa `EmailService` e `_tenant_billing_emails(db, tenant_id)`.
- **Cache:** `billing_daily_job` chama `invalidate_subscription_blocked_all()` quando `apply_grace_policy` alterou assinaturas **ou** quando as notificações sinalizaram mudança relevante (ex.: cortesia que reativou tenant).
- **Task legada:** `app.worker.tasks.apply_billing_grace_policy` — apenas apply_grace_policy (mantida para compatibilidade).
- **Beat:** `app/worker/celery_app.py` — `beat_schedule`: `billing-daily-job` com `crontab(hour=3, minute=0)`.
- **Execução:** `celery -A app.worker.celery_app worker -l info` e `celery -A app.worker.celery_app beat -l info`.

---

## 9. Configuração (configuracoes e ambiente)

**Módulos de configuração relacionados a gateway/pagamento:**
- **`app/core/billing_config.py`** — Leitura de config da plataforma (billing_* no DB ou env): access token MP, webhook secret, APP_URL, valor mensal, descontos. Usado em billing (assinatura) e em modo "plataforma" (vendas e checkout vitrine).
- **`app/services/payments/credentials.py`** — Criptografia de credenciais de provedores por estabelecimento (env: `PAYMENT_CREDENTIALS_SECRET` ou `PAYMENT_CREDENTIALS_PASSWORD`). Usado em Recebíveis (payment_provider_configs).
- **`app/core/pagbank_config.py`** — URL base do OAuth PagBank Connect (sandbox/produção).

**Tabela configuracoes (chaves billing_*):** Podem ser definidas pelo Super Admin em Admin Billing > Config ou > Valor e descontos, com fallback para variáveis de ambiente.

| Chave | Descrição | Fallback env |
|-------|-----------|--------------|
| billing_mp_access_token | Access Token Mercado Pago | MP_ACCESS_TOKEN |
| billing_mp_public_key | Public Key (frontend/brick) | MP_PUBLIC_KEY |
| billing_mp_webhook_secret | Webhook Secret (assinatura x-signature) | MP_WEBHOOK_SECRET |
| billing_app_url | URL base da aplicação | APP_URL |
| billing_valor_mensal_centavos | Valor padrão mensalidade (centavos) | — (default 49000) |
| billing_valor_aplicar_a | Aplicar valor a: todos \| novos | — (default novos) |
| billing_desconto_percent | Desconto em % (0–100) | — (default 0) |
| billing_desconto_escopo | Escopo desconto: todos \| ca \| admin_cliente \| especifico | — (default todos) |
| billing_desconto_tenant_ids | IDs de tenants (escopo=especifico), separados por vírgula | — |
| payment_lojas_gateway_self_service | Se lojas (CA/Admin) podem criar/editar gateways em Recebíveis | — (default true se chave ausente) |

**Config (MP) alinhada à doc Mercado Pago:** Access Token no header (nunca query param); validação do token com GET **api.mercadolibre.com/users/me** (doc oficial). Credenciais: Suas integrações → Credenciais (Access token de teste ou produção). Webhook Secret: Suas integrações → Webhooks → Configurar notificações → revelar Secret.

**Validação do token:** O badge "Mercado Pago: Conectado" na lista de tenants só é exibido quando GET `/api/v1/admin/billing/config/validate` retorna `mp_valid: true` (chamada real à API do MP). Caso contrário: "Token inválido ou sem permissão" (com mensagem no title).

## 10. Variáveis de ambiente

| Variável | Uso |
|----------|-----|
| MP_ACCESS_TOKEN | Token de acesso Mercado Pago (API server-to-server: criar preferência, GET payment). |
| MP_WEBHOOK_SECRET | Secret para validar assinatura do webhook (x-signature). |
| APP_URL | URL base da aplicação (ex.: https://seu-dominio.com) para notification_url e back_urls do Checkout Pro. |

**Credenciais:** Não usar Client Secret como Access Token. O Access Token (Produção ou Teste) é obtido no painel do Mercado Pago em Credenciais. Ver `payment.md` na raiz do projeto para referência de credenciais (Public Key, Client ID, Client Secret são distintos do Access Token).

### 10.1 Referência — Aplicação Mercado Pago (credenciais em uso no sistema)

**Credenciais configuradas no sistema (banco/config):**

| Campo | Valor |
|-------|--------|
| **Client ID (N.º da aplicação)** | 8273969458446033 |
| **User ID** | 338366730 |
| **Public Key** | APP_USR-2bafde9c-9692-42cb-88ae-35a1faea17e4 |
| **Access Token** | APP_USR-8273969458446033-030911-e2901c389e57f2d7becf83f065716092-338366730 |
| **Client Secret** | AcS26GaH2az1UKX6zEZPxOHp03HZxh1J |

**Webhook Secret:** Configurar em Admin Billing > Config ou **MP_WEBHOOK_SECRET** quando disponível (Painel MP: Webhooks → Configurar notificações → revelar Secret).

**URL de notificação (webhook) — obrigatória no painel MP:**  
Use a URL **canônica**, sem redirecionamento. O Nginx redireciona `ibix.com.br` → `www.ibix.com.br` (301); o MP não segue redirect em POST, então use **com www**:

- `https://www.ibix.com.br/api/webhooks/mercadopago`  
  (https, **com www**, sem barra no final)

**URLs de redirecionamento (obrigatórias no painel MP):**

- `https://www.ibix.com.br/billing/success`
- `https://www.ibix.com.br/billing/failure`
- `https://www.ibix.com.br/billing/pending`

Ou apenas a URL base `https://www.ibix.com.br` se o painel aceitar uma única URL.

---

## 11. Preferência Checkout Pro e valor

- **Valor e desconto:** O valor enviado ao MP (unit_price) é calculado por tenant via `_valor_centavos_para_tenant(db, tenant_id)`. **Prioridade:** 1) contrato_comercial ativo do tenant (valor_mensal_centavos); 2) valor configurado admin (billing_config) com desconto por escopo. A assinatura (subscription) tem `valor_mensal_centavos` atualizado ao criar preferência e ao aplicar "valor a todos".
- **Payer:** A preferência envia dados completos do pagador quando há usuário logado (pay-now): `email`, `first_name`, `last_name` (derivados de `Usuario.nome`), `identification` (CPF do usuário); quando o tenant possui **Empresa** padrão (`Tenant.default_empresa`), envia também `payer.phone` e `payer.address` (boas práticas MP para aprovação). Sem usuário (admin gera link), apenas o mínimo é enviado quando houver e-mail.
- **Items:** Cada item da preferência inclui `id` (ex.: `sub-{subscription.id}`), `title`, `description` ("Assinatura mensal do PDV Ibix"), `category_id` ("services"), `quantity`, `unit_price`, `currency_id` — alinhado às recomendações MP para redução de recusas por antifraude.
- **Payment methods:** Não se envia restrição rígida de `payment_methods` (evita botão "Pagar" desabilitado no MP). Boleto disponível; valor mínimo boleto no MP é R$ 4,00.

### 11.1 Alinhamento com a documentação Mercado Pago (criar e configurar preferência)

O fluxo segue a documentação oficial do MP: **Criar e configurar uma preferência de pagamento (Server-Side)** → **Obter o identificador da preferência** → **Integração Checkout Pro (web)**.

| Etapa (doc. MP) | No sistema |
|-----------------|------------|
| **Criar preferência no backend** com `items` (title, quantity, unit_price) | `app/services/billing_service.py` — `create_checkout_preference()` monta o payload com `items` (título "PDV Ibix - Assinatura mensal", quantity 1, unit_price em BRL), `back_urls`, `notification_url`, `external_reference`, `payer.email`. |
| **Chamar a API** para criar a preferência | `app/integrations/mercadopago.py` — `MercadoPagoClient.create_preference(payload)` faz **POST** em `https://api.mercadopago.com/checkout/preferences` com o payload. |
| **Obter o ID da preferência** na resposta (propriedade `id`) | `billing_service.create_checkout_preference`: `preference_id = result.get("id")`; o valor é gravado em `sub.mp_preference_id` e retornado na API. |
| **Usar o identificador** e o tipo de integração (Checkout Pro) | A resposta do MP inclui **init_point** (e em teste **sandbox_init_point**). O backend retorna `init_point` e `preference_id`; o front abre o **init_point** em nova aba (página do Checkout Pro). |
| **Uma nova preferência por pedido/fluxo** | Cada clique em "Pagar agora" (cliente) ou "Gerar cobrança" (admin) chama `create_checkout_preference` e gera uma **nova** preferência para aquela assinatura/tenant. |

**Payload enviado ao MP (equivalente):**

- `items`: um item com `id` (ex.: sub-{subscription.id}), `title`, `description`, `category_id` ("services"), quantity 1, unit_price em R$, currency_id BRL.
- `back_urls`: success, failure, pending (base em APP_URL: `/billing/success`, `/billing/failure`, `/billing/pending`).
- `auto_return`: "approved".
- `notification_url`: `{APP_URL}/api/webhooks/mercadopago`.
- `external_reference`: id da assinatura (subscription.id).
- `payer`: quando há usuário pagador — `email`, `first_name`, `last_name` (de Usuario.nome), `identification` (type CPF, number só dígitos); quando o tenant tem Empresa padrão — `phone` (area_code, number) e `address` (zip_code, street_name, street_number, city_name, state_name) a partir de Empresa.

### 11.2 Preferência 100% (recomendações MP — aprovação)

O request de Preferências atende às recomendações do Mercado Pago para melhorar o índice de aprovação e reduzir recusas do mecanismo de prevenção de fraudes:

| Recomendação MP | No sistema |
|-----------------|------------|
| payer.first_name | Derivado de `Usuario.nome` (primeira palavra) em `create_checkout_preference` quando há `payer_user_id`. |
| payer.last_name | Derivado de `Usuario.nome` (restante) quando há `payer_user_id`. |
| payer.identification | CPF do usuário (type "CPF", number só dígitos) quando `Usuario.cpf` válido. |
| payer.phone (boas práticas) | Quando o tenant do pagador tem `default_empresa` com `Empresa.telefone`, enviado como `area_code` + `number`. |
| payer.address (boas práticas) | Quando o tenant tem `default_empresa` com endereço (cep, endereco, numero, cidade, uf), enviado no formato MP. |
| items.id | Enviado como `sub-{subscription.id}`. |
| items.description | "Assinatura mensal do PDV Ibix". |
| items.category_id | "services". |

Funções auxiliares em `billing_service.py`: `_split_payer_name`, `_normalize_cpf_for_mp`, `_get_empresa_for_tenant`, `_build_payer_phone`, `_build_payer_address`. O webhook não é alterado; as recomendações aplicam-se apenas ao payload da **Preferência**.

**Onde o init_point é usado no front:** `app/templates/financeiro/assinatura.html` (POST `/api/v1/billing/pay-now` → abre `data.init_point` ou `data.sandbox_init_point`); `app/templates/admin/billing_tenant_detail.html` (create-charge → `window.open(d.init_point)`).

## 12. Scripts e ambiente virtual

- **Ajustar valor das assinaturas:** O script `scripts/ajustar_assinaturas_1real.py` atualiza todas as assinaturas para 100 centavos (R$ 1,00) para testes. Executar **sempre no ambiente virtual:** `.venv/bin/python scripts/ajustar_assinaturas_1real.py`. Para voltar a R$ 490,00: alterar constante no script ou usar a página Admin Billing > Valor e descontos e "Aplicar valor a todas as assinaturas atuais".
- **Valor padrão em código:** `app/services/billing_service.py` — `VALOR_MENSAL_CENTAVOS = 49000`; o valor efetivo vem de `billing_config.get_valor_mensal_centavos(db)` quando configurado.

## 13. Checklist de produção

- MP_ACCESS_TOKEN, MP_WEBHOOK_SECRET e APP_URL definidos no ambiente (.env ou variáveis).
- Webhook acessível em HTTPS: `{APP_URL}/api/webhooks/mercadopago`. Não confiar apenas no redirect; webhook chama GET https://api.mercadopago.com/v1/payments/{id} antes de atualizar assinatura.
- Idempotência garantida por **webhook_events** (provider + event_key). Event_key = `payment:{id}`.
- Trial ao cadastro: ao criar **Tenant** (ex.: webhook gateway em `_process_billing_payload` em `app/api/v1/billing.py`), chamar `billing_service.create_trial_subscription(db, tenant.id)` (status=trial, 30 dias, grace_days=15).
- Job diário (Celery Beat) rodando: task **billing_daily_job** (notificações trial_d7…pastdue_d15 + apply_grace_policy para D+15 bloqueio).
- Preferência Checkout Pro: items com unit_price conforme valor configurado (e desconto por escopo); back_urls e notification_url com APP_URL; payer.email quando disponível.
- Persistir raw_json do pagamento em **payments** para auditoria.

---

## 14. Arquivos principais

| Componente | Caminho |
|------------|---------|
| Modelo assinatura billing | `app/models/subscription_billing.py` (inclui `qtd_pdvs_contratados`) |
| Modelo preços PDV | `app/models/preco_pdv.py` |
| Modelos contrato comercial e aditivo | `app/models/contrato_comercial.py`, `app/models/contrato_aditivo.py` |
| Modelos códigos desconto, divulgadores, regras | `app/models/codigo_desconto.py`, `app/models/divulgador.py`, `app/models/divulgador_regra.py` |
| Modelos payment, webhook_event, billing_notificacao | `app/models/payment.py`, `app/models/webhook_event.py`, `app/models/billing_notificacao.py` |
| Guard e allowlist | `app/core/subscription_guard.py` |
| Resolve tenant pagador | `app/core/scope.py` — `resolve_tenant_pagador` |
| Config valor/desconto | `app/core/billing_config.py` — get_valor_mensal_centavos, get_valor_aplicar_a, get_desconto_*, get_desconto_tenant_ids; chaves billing_* |
| Cliente Mercado Pago | `app/integrations/mercadopago.py` — parse_x_signature, verify_webhook_signature, MercadoPagoClient (create_preference, fetch_payment, **validate_token** — GET api.mercadolibre.com/users/me) |
| Serviço billing completo | `app/services/billing_service.py` — **_valor_centavos_para_tenant**, **_tenant_tem_desconto**; apply_grace_policy, create_trial_subscription, create_checkout_preference (valor/desconto por tenant), process_payment_webhook, process_billing_notifications |
| Schemas billing | `app/schemas/billing.py` — MySubscriptionResponse, PayNowResponse, PaymentListItem, Admin* |
| Schemas contrato e preço | `app/schemas/contrato_comercial.py` — ContratoComercialCreate/Response, ContratoAditivoCreate/Response, MeusLimitesResponse; `app/schemas/preco_pdv.py`; `app/schemas/codigo_desconto.py` |
| API billing (cliente) | `app/api/v1/billing.py` — my-subscription, **meus-limites**, pay-now, my-payments; webhook genérico /billing/webhook |
| API admin billing | `app/api/v1/admin_billing.py` — tenants, tenant/{id}, create-charge, block, unblock, config, **config/validate**, **preco**, **preco/aplicar-valor-todos** |
| API preços PDV (admin) | `app/api/v1/precos_pdv.py` — CRUD precos_pdv (SuperAdmin) |
| API contratos comerciais | `app/api/v1/contratos_comerciais.py` — CRUD contratos e aditivos (SuperAdmin/Admin) |
| API códigos desconto | `app/api/v1/codigos_desconto.py` — CRUD codigos, divulgadores, regras (SuperAdmin/Admin); validar público |
| Webhook Mercado Pago | `app/api/webhooks_mercadopago.py` — POST /mercadopago (incluído com prefix /api/webhooks). Alternativa: `app/api/webhooks_payments.py` — POST /api/webhooks/payments/mercadopago delega para o mesmo handler. |
| Checkout marketplace (vitrine) | `app/services/payments/checkout_marketplace_service.py` — create_checkout_for_pedido, create_retry_checkout_for_pedido, _resolve_provider_and_credentials (modo_recebimento). |
| Connect OAuth PagBank | `app/api/v1/payments_connect.py` — GET /payments/connect/pagbank/start, GET /payments/connect/pagbank/callback. |
| Middleware redirect | `main.py` — `subscription_block_redirect` |
| Rotas HTML Assinatura e redirects | `main.py` — GET /financeiro/assinatura; GET /billing/success, /billing/failure, /billing/pending (redirect → /financeiro/assinatura) |
| Rotas HTML Admin Billing | `main.py` — GET /admin/billing/tenants, /admin/billing/tenant/{id}, /admin/billing/config, **/admin/billing/preco**, **/admin/billing/precos-pdv**, **/admin/billing/codigos-desconto** (guard Super Admin/Admin) |
| Templates admin billing | `app/templates/admin/billing_tenants.html`, `billing_tenant_detail.html`, `billing_config.html`, **billing_preco.html**, **precos_pdv.html**, **codigos_desconto.html** |
| Template Assinatura | `app/templates/financeiro/assinatura.html` |
| Sidebar (menu bloqueado + Cobranças Admin) | `app/templates/components/sidebar.html` — subscription_blocked → só Assinatura; Superadministrador → "Cobranças (Admin)" → /admin/billing/tenants |
| Tasks e Beat | `app/worker/tasks.py` — apply_billing_grace_policy, **billing_daily_job**; `app/worker/celery_app.py` — beat_schedule billing-daily-job (03:00) |
| Migrações | `y56aa458n4x0_add_subscriptions_billing.py`; `z67bb569o5y1_add_payments_webhook_events_billing_notificacoes.py`; **`nn33pp469v9_fase2_precos_contrato_desconto.py`**; **`oo44qq570w0_add_qtd_pdvs_subscriptions.py`** |
| Variáveis de ambiente | `.env.example` — MP_ACCESS_TOKEN, MP_WEBHOOK_SECRET, APP_URL |

---

## Apêndice — Origem das informações (CA recebimento e gateway)

| Informação | Origem |
|------------|--------|
| Rotas HTML Recebíveis e redirect Pagamentos | `main.py` (linhas 1999–2016): `@app.get("/negocio/recebiveis")`, `@app.get("/negocio/pagamentos")` → redirect para `/negocio/recebiveis`. |
| Template e texto “configuração de recebimento (gateway)” | `app/templates/meu_negocio/pagamentos/index.html`: título Recebíveis, select estabelecimento, tabela de configs, texto “integração de recebimento (gateway)”, “Fase 1, apenas Mercado Pago”. |
| Modal “Nova configuração”, Gateway Mercado Pago, credenciais JSON, POST configs | `app/templates/meu_negocio/pagamentos/index.html`: modal `modalConfigPagamentoCustom`, select `configProviderCode` (option mercadopago), textarea `configCredentials`, `authFetch('/api/v1/payments/configs', { method: 'POST', ... })`. |
| APIs de configs e transações (listar configs, transações, retry, reconcile, comprovante) | `app/templates/meu_negocio/pagamentos/index.html`: `authFetch('/api/v1/payments/configs?estabelecimentoId=' + estabId)`, `authFetch('/api/v1/payments/transactions?...')` (status all|paid,authorized|pending,failed), `authFetch('/api/v1/payments/retry/' + uuid, { method: 'POST' })`, `authFetch('/api/v1/payments/reconcile/' + uuid, { method: 'POST' })`, `authFetch('/api/v1/payments/transactions/' + uuid + '/comprovante')` — comprovante via fetch (evita problema de cookie em navegação direta). |
| Item de menu “Recebíveis” no sidebar | `app/templates/components/sidebar.html`: `<a href="/negocio/recebiveis">` com ícone dollar-sign e condição `negocios.venda:visualizar` ou `negocios.financeiro:visualizar` ou `negocios`. |
| Inclusão do router de payments na API | `main.py`: registro do router `app.api.v1.payments` (prefixo `/api/v1`). |
| Escopo por estabelecimento (CA) e endpoints configs/process/transactions | `app/api/v1/payments.py`: `get_cliente_scope_dep`, `forbid_cliente_access`, `_allowed_cliente_ids(scope)`; Fase 1 só `mercadopago`. |
| Fluxo de processamento (process, orchestrator, transação) | `app/api/v1/payments.py` (POST `/payments/process`) e `app/services/payments/orchestrator.py`: uso de `PaymentProviderConfig` por `cliente_id`, criação de `PaymentTransaction`. |
| Checkout vitrine (modo_recebimento) | `app/services/payments/checkout_marketplace_service.py`: `create_checkout_for_pedido` e `_resolve_provider_and_credentials` — quando empresa fiscal do CA está em modo plataforma, usa billing MP; quando direto, usa config do CA em Recebíveis. Chamado por POST `/api/v1/loja/checkout` quando há gateway ativo. |
| Preferência MP (aprovação) | `providers_marketplace.py` e `checkout_marketplace_service.py`: envia `payer` (first_name, last_name, email) e `items` (id, title, description, category_id) na preferência — melhora índice de aprovação MP. |
| Webhook e reconciliação com venda_pagamentos | `app/api/webhooks_mercadopago.py`: reconciliação de `payment_transactions`, `_sync_venda_pagamento_from_transaction`. |
| Uso de `/payments/process` ao finalizar venda (Nova Venda) | `app/templates/meu_negocio/vendas/index.html`: `processarPagamentoGateway(…)`, `authFetch('/api/v1/payments/process', …)`; registro em `venda_pagamentos` após criação da venda. |
| Uso de `/payments/process` no PDV | `app/static/js/pdv.js`: `apiFetch("/api/v1/payments/process", ...)`. |
| Modelo de config por estabelecimento | `app/models/payment_provider_config.py`: `PaymentProviderConfig` com `cliente_id`, `provider_code`, `credentials_encrypted`, etc. |

---

**Última atualização:** 2026-07-18 — **Recebíveis / self-service:** documentada chave `payment_lojas_gateway_self_service` (§ 2.6 e § 9); UI não assume edição permitida no filtro «Todos» (`GET /payments/modo-recebimento` sem `clienteId`). — 2026-03-19 — **Recebíveis (correções chat):** Transações com filtros Todas/Pagas/Pendentes e falhas; API retorna `pedido_id`, `numero_pedido`, `paid_at`; botão Comprovante (fetch para API `/payments/transactions/{uuid}/comprovante`, abre HTML em nova janela); botão Verificar status (POST reconcile); rota HTML `/negocio/recebiveis/comprovante/{uuid}` mantida (usa `user_id`, não `request.state.user`). Auth: backend e middleware aceitam `pdv_solumatica_token` e `pdv_automscale_token`. — 2026-03-17 — **Checkout vitrine e modo_recebimento:** § 2.5.1 passa a citar que o checkout da vitrine (create_checkout_for_pedido) aplica a mesma regra de modo_recebimento (plataforma = billing MP; direto = config CA). Apêndice: fluxo checkout vitrine, arquivos checkout_marketplace_service, payments_connect, webhooks_payments. § 9: módulos de config (billing_config, credentials, pagbank_config). — 2026-03-10 — § 11 e 11.2 Preferência 100% MP: payer (first_name, last_name, identification, phone, address) e items (id, description, category_id) no request de Preferências para melhorar índice de aprovação; funções auxiliares em billing_service. — 2026-03-09 — § 10.1 Credenciais de teste atualizadas (App 2856364165337130, User ID 3255266694, Public Key APP_USR-850815ad-..., Access Token no sistema). — § 11.1 Alinhamento com a documentação MP (criar e configurar preferência server-side, obter ID, init_point, uma preferência por fluxo, payload e uso no front). — § 10.1 Referência aplicação Mercado Pago. — Seção 2.6 CA: como recebe o pagamento, onde configura o gateway; Apêndice origem das informações (fontes). — 2026-03-02 — **Valor e descontos / Aplicar a todos:** Opção ao aplicar valor a todas as assinaturas: "Respeitar códigos promocionais" ou "Substituir em todas (ignorar códigos)" (body `respeitar_codigos_promocionais`). **Específico (tenants):** GET tenants com `apenas_com_ca=true` para o select "Tenants com desconto" — lista apenas tenants com Cliente Administrador (C), não CF. — 2026-03-02 **Códigos de desconto e Representante:** Criação de código vinculada obrigatoriamente a um Representante (Administrador). Modal "Novo Código" lista usuários com função Administrador; body aceita `representante_usuario_id`; backend encontra ou cria divulgador e associa ao código. — 2026-02-20 **Fase 2 Estrutura Comercial:** Tabela `precos_pdv`; `contrato_comercial` + `contrato_aditivos`; `subscriptions.qtd_pdvs_contratados`; checagem limite PDV (HTTP 402); `codigos_desconto` + `divulgadores` + `divulgador_regras`; UI admin `/admin/billing/codigos-desconto` e `/admin/billing/precos-pdv`. — Anterior: Valor e descontos, validação token MP, config doc MP.
