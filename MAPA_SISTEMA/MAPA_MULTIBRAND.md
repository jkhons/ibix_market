# MAPA MULTI-BRAND — PDV Ibix

**Fonte única** para modelo de marcas (Ibix origem + marcas derivadas), resolução por Host, gating de módulos, RLS e deploy multi-domínio.

**Plano mestre:** [.cursor/plans/multi-brand_modulos_seguranca_7478796e.plan.md](../.cursor/plans/multi-brand_modulos_seguranca_7478796e.plan.md)

**Regras Cursor (Fase 7):** `.cursor/rules/multibrand-no-hardcode.mdc`, `modulo-gating.mdc`, `tenant-rls.mdc`, `conflito-dados-migracao.mdc`, `seguranca-dominio.mdc`

---

## 1. Conceitos

| Conceito | Descrição |
|----------|-----------|
| **Marca origem** | Ibix (`brands.is_origem = true`) — dona da plataforma; marketplace e billing central |
| **Marca derivada** | Ex.: Solumática — mesmo código, branding e catálogo de módulos distintos |
| **BrandContext** | Objeto em `request.state.brand` (slug, nome, logos, `seo_base_url`, etc.) |
| **Módulo de produto** | Slug em `brand_modules` (`core`, `marketplace`, `certificados`, `calibracao`) |
| **Gating efetivo** | `brand_modules(brand) ∩ tenant_entitlements ∩ RBAC` |

**Regra de ouro:** herança visual da origem (defaults de logo/cores) **não** autoriza fallback de dado de negócio (tenant, pagamento, escopo).

---

## 2. Modelo de dados (Alembic br01–br35)

### Tabelas principais

| Tabela | Função |
|--------|--------|
| `brands` | Cadastro de marca (`slug`, `nome_exibicao`, `is_origem`, `seo_base_url`, assets visuais) |
| `brand_domains` | Host → `brand_id` (allowlist; único por host) |
| `brand_modules` | Módulos habilitados por marca (`brand_id`, `module_slug`) |
| `tenants.brand_id` | FK — tenant pertence a uma marca; slug único **por marca** `UNIQUE(brand_id, slug)` |

### Cadeia de migrações

`br01` → `br02` → `br03` → `br31` → `br32` → `br33` → `br34` → **`br35_rls_policies` (head)**

- **br33:** índices compostos `(tenant_id, …)` / `(brand_id, …)`
- **br35:** RLS em 26 tabelas com `tenant_id`; política `tenants.rls_tenants_scope`
- **br36:** `pii:visualizar` atribuída à role **Cliente Administrador** (listagem de clientes sem máscara CPF/CNPJ no tenant)

### Conflitos e unicidade

- **Tenant.slug:** escopo `(brand_id, slug)` — nunca global
- **Consumidor marketplace:** `UNIQUE(tenant_id, LOWER(email))` (escopo Ibix)
- **Reconciliação de módulos:** `INSERT … ON CONFLICT DO NOTHING` — sem `DELETE` de entitlement ativo
- **Pré-migração:** `scripts/audit_multibrand_pre_migration.py`

---

## 3. Resolução por Host

1. Middleware `brand_resolution_middleware` lê `Host` / `X-Forwarded-Host`
2. Busca em `brand_domains` (cache Redis)
3. Host desconhecido → marca **origem** (Ibix), sem aceitar escopo arbitrário
4. Popula `request.state.brand`, `request.state.brand_module_slugs`

**Código:** `app/services/brand_service.py`, `app/core/middleware.py`

---

## 4. Matriz produto × módulo (atual)

| Marca | Módulos | Marketplace /loja |
|-------|---------|-------------------|
| **Ibix** | `core`, `marketplace` | Habilitado |
| **Solumática** | `core` apenas | **403** (middleware + API guards) |
| **Certipeso** (futuro) | `core` (+ módulos quando existirem) | Bloqueado até cadastro |

Módulos `certificados` e `calibracao` existem no catálogo; implementação funcional adiada — rotas devem retornar **403** fora do catálogo da marca.

---

## 5. Gating (3 portas)

| Camada | Mecanismo |
|--------|-----------|
| **Menu HTML** | `check_html_module_permission` + catálogo da marca |
| **Rotas HTML** | `marketplace_brand_gate_middleware` — paths em `brand_module_gating.py` |
| **API** | `MARKETPLACE_ROUTER_DEPENDENCIES`, `assert_marketplace_ibix_brand` |

Bloqueio = **HTTP 403** explícito; sem redirect silencioso para Ibix.

Detalhe RBAC: [MAPA_RBAC.md](MAPA_RBAC.md) § 0.13

---

## 6. Row-Level Security (RLS)

- **Flag:** `RLS_ENABLED` (env; default `false` em dev legado)
- **Sessão:** `open_db_session()` / `get_db` → `SET LOCAL app.current_tenant`, `app.current_brand`, `app.bypass_rls`
- **Superadmin:** `app.bypass_rls = on`
- **Produção efetiva:** role da app **sem** `BYPASSRLS`; migrador com role separada
- **Verificação:** `scripts/verify_rls_policies.py`, `scripts/backup_pre_rls.sh`, `scripts/rollout_multibrand_fase6.sh`

**API marketplace consumidor (`/api/v1/loja/*`, `/api/v1/marketing-vitrine/*`):** `ensure_marketplace_loja_rls` ([marketplace_rls.py](../app/core/marketplace_rls.py)) aplica `bypass_rls=true` + `brand_id` Ibix — catálogo cross-tenant e pedidos multi-loja; isolamento por JWT (`comprador_id`), gating de módulo e `assert_marketplace_ibix_brand`. WebSocket `/ws/loja/consumidor` usa `open_db_session(bypass_rls=True)`.

**Autenticação PDV com RLS ativo (2026-06-18):**

| Momento | Sessão DB | Motivo |
|---------|-----------|--------|
| **Pré-auth** (`POST /auth/login`, cadastro, esqueci/redefinir senha) | `get_db_pre_auth()` → `bypass_rls=true` | `usuarios` com `tenant_id` ficam invisíveis sem bypass; login falhava com 401 genérico |
| **Pós-auth (cookie JWT)** | `populate_pdv_user_context()` → bypass temporário, resolve `tenant_id`, reaplica RLS | Middleware preenche ContextVar antes das rotas HTML/API; evita loop `/login` ↔ `/dashboard` |
| **Rotas autenticadas** | `get_db()` com `tenant_id` / `bypass_rls` do contexto | Superadmin: bypass; demais: política `rls_{tabela}_tenant` |

Arquivos: [connection.py](../app/database/connection.py) (`get_db_pre_auth`), [request_context.py](../app/core/request_context.py), [db_session_scope.py](../app/core/db_session_scope.py) (`after_begin` reaplica SET LOCAL pós-commit).

**Pendências operacionais (P0):** concluídas em prod (`RLS_ENABLED=true`, `DB_USER=pdv_app`, Celery `worker_db_session`, smoke mobile). EXPLAIN: `scripts/explain_rls_hot_queries.sh`.

**Tabelas com `cliente_id` sem RLS (~30):** decisão **mantida** — escopo por `ClienteScope`/RBAC na aplicação; RLS permanece em entidades com `tenant_id`. Novas tabelas operacionais multi-tenant devem nascer com `tenant_id NOT NULL` + política RLS (checklist §12).

---

## 7. Segurança por domínio

| Área | Implementação |
|------|----------------|
| **CORS** | `CORS_ORIGINS` + origens de `brand_domains` / `seo_base_url` — [hardening.py](../app/core/hardening.py) |
| **CSP** | `build_csp_header(brand)` por marca |
| **Cookies** | Host-only — [brand_cookie.py](../app/core/brand_cookie.py) (sem `Domain` compartilhado); `clear_pdv_auth_cookies()` no logout |
| **OAuth / redirect** | `public_origin_from_request()` / `brand.seo_base_url` (PagBank, vitrine social) |
| **Rate limit** | Chave `{brand_slug}:{ip}` em login/cadastro/loja |
| **/metrics** | Apenas localhost (Nginx + middleware) |

Deploy: [MAPA_DEPLOY_SERVICOS.md](MAPA_DEPLOY_SERVICOS.md) § 2.1 e § 4

---

## 8. Templates e front

- **PDV:** `get_template_context` → `{{ brand.nome_exibicao }}`, `{{ brand.logo_url }}`, etc.
- **Vitrine:** `_loja_context` / `base_loja.html`
- **Proibido:** literais `"Ibix"`, `"Solumática"`, paths fixos de asset de marca no HTML/JS

---

## 9. APIs com escopo de marca

| Área | Comportamento |
|------|----------------|
| **Auth / cadastro** | `brand_id_from_request` ao criar tenant |
| **Billing** | Slug de tenant único por `brand_id` |
| **Admin Superadmin** | `resolve_admin_brand_scope(request, db)` — marca derivada: escopo obrigatório do Host; origem Ibix: `brand_id` query opcional ou visão global |
| **Usuários / vendas / clientes** | Superadmin em host derivado: filtro por `tenants.brand_id` (`usuarios.py`, `get_cliente_scope_dep`) |
| **Dashboard / hierarquia / billing tenants** | Default de `brand_id` pelo Host; resposta JSON com `brand_scope` onde aplicável |
| **UI admin** | `brand_scope_banner.html` + badge navbar (`brand_scope.scope_label`); sidebar marketplace-only com `brand_has_marketplace` |
| **Marketplace `/api/v1/loja/*`** | Guard marketplace — só marca Ibix |
| **LGPD admin** | `GET/POST /api/v1/admin/lgpd/*` com `brand_id` opcional |
| **PagBank Connect** | `redirect_uri` por origem pública da marca |

Detalhe endpoints: [MAPA_DE_API.md](MAPA_DE_API.md) § 20

---

## 10. Deploy multi-domínio

- **Mesmo upstream:** todos os `server_name` → `127.0.0.1:8000`
- **Nginx:** `scripts/deploy/nginx/solumatica-brand.conf`, `obter-certificado-multibrand.sh`
- **Certbot:** certificado por domínio de marca (Solumática, futuro Certipeso)
- **`.env`:** `CORS_ORIGINS` deve listar **todas** as origens de produção por marca

---

## 11. Planos legados (superados)

Os planos abaixo foram **consolidados** neste mapa e no plano multi-brand; não usar como fonte paralela:

- `landing_solumatica_a_partir_do_certipeso`
- `rebrand_pdv_solumatica_e_deploy`
- `escopo_projeto_solumatica_auto`

---

## 12. Checklist para desenvolvedores / IA

- [ ] Consultei este mapa ou a regra Cursor correspondente?
- [ ] Branding via `request.state.brand` / `{{ brand.* }}` (sem hardcode)?
- [ ] Rota opcional passou por gating (403 se indisponível)?
- [ ] Tabela nova com `tenant_id NOT NULL` + RLS na migração?
- [ ] Unicidade escopada por `brand_id` onde aplicável?
- [ ] Domínio novo em `brand_domains`, não no código?

---

## 13. Enterprise (Fase 9)

| Item | Implementação |
|------|----------------|
| **RLS efetivo** | `scripts/sql/create_pdv_app_role.sql` → `DB_USER=pdv_app`, `RLS_ENABLED=true` |
| **Checagem startup** | `app/core/enterprise_checks.py`; `ENTERPRISE_STRICT_STARTUP=true` quando pronto |
| **Workers Celery** | `app/worker/db_task.py` — `worker_db_session()` (bypass plataforma ou tenant explícito) |
| **Segredos** | `app/core/secrets_provider.py` (env + `SECRETS_DIR`); extensível Vault/AWS |
| **Logs estruturados** | `app/core/structured_log_context.py` — `tenant_id`/`brand_id`/`request_id` automáticos |
| **Ciclo de vida tenant** | `GET/POST /api/v1/admin/tenant-lifecycle/tenant/{id}/*` (status, suspend, resume, offboarding) |
| **DR** | RPO 24h / RTO 4h — `scripts/dr/runbook_dr.md`, `verify_dr_readiness.sh` |
| **CI** | `.github/workflows/ci.yml` — pytest + isolamento |
| **WAF/DDoS** | Camada 1: Cloudflare (recomendado); camada 2: rate limit app (`rate_limiter.py`) |
| **Escala (gatilho)** | Particionamento/cell-based quando: p95 query > 2s sustentado, >10M linhas/vendas ou noisy neighbor recorrente; ver `br33` comentários |

Scripts: `scripts/verify_enterprise_readiness.sh`, `scripts/migrations/zero_downtime_checklist.md`

---

**Última atualização:** 2026-06-18  
**Versão:** 1.2  
**Status:** Documentação ativa — Fases 8–9 do plano multi-brand (+ correções RLS auth/logout/PII CA)
