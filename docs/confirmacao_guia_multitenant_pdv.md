# Confirmação: Guia Técnico Multi-Tenant vs PDV Ibix

Como seu consultor técnico, segue a conferência do guia "Protegendo Seu Sistema Multi-Tenant" em relação ao código atual do PDV Ibix. Objetivo: **evitar conflitos entre tenants** e alinhar o que já está correto com o que exige atenção.

---

## Visão geral do modelo do PDV

O PDV usa **dois eixos de isolamento** (não só `tenant_id` em todas as tabelas):

1. **Tenant** (`tenants.id`): organização que paga a assinatura. Usado em: `usuarios`, `subscriptions`, `billing_notificacoes`, `audit_log`, `tenant_entitlements`, `contrato_comercial`.
2. **Cliente/Estabelecimento** (`clientes.id`) + **CA** (`usuario_id_cliente_admin`): dados operacionais (vendas, notas, estoque, movimentações) são filtrados por **escopo de cliente** (`ClienteScope`, `get_allowed_cliente_ids`) ou por **CA** (`get_current_cliente_admin_id`). Como cada cliente pertence a um único CA e cada CA a um tenant, o isolamento por tenant é respeitado indiretamente.

Ou seja: o guia fala em “sempre `tenant_id`”; no PDV, parte das tabelas usa `tenant_id` e parte usa `cliente_id`/CA, com a mesma finalidade de isolamento.

---

## CAMADA 1: Isolamento de dados

| Guia | PDV Ibix | Status |
|------|----------------|--------|
| Tabelas com `tenant_id`; índice composto `(tenant_id, id)` | `usuarios`, `subscriptions`, `billing_notificacoes`, `audit_log`, `tenant_entitlements`, `contrato_comercial` têm `tenant_id` e índices. Vendas, notas, pedidos, estoque usam `cliente_id` ou `usuario_id_cliente_admin` (CA). | **Parcial** – modelo híbrido |
| NUNCA query sem `tenant_id` | Queries operacionais usam `ClienteScope.allowed_ids` ou `Estoque.usuario_id_cliente_admin == ca_id`; billing/admin usam `tenant_id`. Não há query “crua” por id sem filtro de escopo nas APIs analisadas. | **Confirmado** (via escopo/CA) |
| Schema separado por tenant | Não utilizado; banco único. | **Não aplicado** (decisão de arquitetura) |

**Conclusão:** Isolamento de dados está coerente com o desenho do sistema. Não há “todas as tabelas com `tenant_id`”, mas as que não têm são protegidas por `cliente_id`/CA. Índices com `tenant_id` existem onde a coluna existe (ex.: `ix_subscriptions_tenant_status`, `ix_billing_notificacoes_tenant_tipo`, `ix_audit_log_tenant_id`, `ix_usuarios_tenant_id`).

---

## CAMADA 2: Autenticação e acesso

| Guia | PDV Ibix | Status |
|------|----------------|--------|
| Middleware captura tenant (subdomínio, header `X-Tenant-ID`, JWT) | Não há subdomínio nem `X-Tenant-ID`. Tenant **não** vem do request; é resolvido no backend a partir do usuário (ex.: `Usuario.tenant_id`, `resolve_tenant_pagador`). | **Diferente** – seguro (não confia no cliente) |
| Validar se tenant existe e está ativo | `SubscriptionGuard` e `is_subscription_blocked`: usam `resolve_tenant_pagador(db, user)` e checam `Tenant.ativo`. Bloqueado = 403 ou redirect para /financeiro/assinatura. | **Confirmado** |
| JWT incluir `tenantId` e validar contra request | JWT contém `sub`, `email`, `role`, `cliente_id` (opcional). **Não contém `tenant_id`**. Tenant é sempre obtido do usuário no banco. | **Diferente** – backend não confia em tenant no token |
| `req.tenantId` disponível nas rotas | Em `add_user_to_request` (main.py) é setado `request.state.tenant_id = str(cid)` onde `cid = payload.get("cliente_id")`. Ou seja, **está sendo guardado cliente_id (estabelecimento), não tenant_id**. Nome enganoso e risco em logs/auditoria. | **Atenção** – nome e valor incorretos |

**Recomendação:** Manter tenant apenas no backend (via usuário). Para logs/auditoria, usar o tenant real: por exemplo em `add_user_to_request` buscar `current_user.tenant_id` (após carregar o usuário) ou passar `tenant_id` derivado do usuário para o handler de exceção, em vez de reutilizar `request.state.tenant_id` como se fosse o tenant da assinatura.

---

## CAMADA 3: RBAC por tenant

| Guia | PDV Ibix | Status |
|------|----------------|--------|
| Permissões com `tenant_id` (cada tenant pode ter roles diferentes) | Roles e permissões são globais (`roles`, `permissoes`, `role_permissoes`). Escopo de **dados** é por usuário: `get_allowed_cliente_ids` / `ClienteScope`. | **Parcial** – RBAC global, escopo por usuário/CA |
| Hierarquia (super_admin, tenant_admin, tenant_user) | Existe: Superadministrador, Administrador, Cliente Administrador, Técnico, Contador, Subcliente, Operador PDV. Controle por role + permissão (módulo:ação) e por escopo de cliente. | **Confirmado** |
| Autorização garante tenant do token = tenant da requisição | Não há “tenant da requisição”; tenant é o do usuário. Subscription guard garante que tenant do usuário não está bloqueado. | **Confirmado** (modelo diferente) |

**Conclusão:** Não há tabela de permissões “por tenant”; o isolamento é por escopo de cliente e por CA, o que atende ao objetivo de “um tenant não acessar dados de outro”.

---

## CAMADA 4: Prevenção de vazamentos

| Guia | PDV Ibix | Status |
|------|----------------|--------|
| Repository Pattern com `tenant_id` obrigatório em todo find/create | Não existe BaseRepository; cada rota usa `ClienteScope` ou `get_current_cliente_admin_id` e aplica filtros (ex.: `Venda.cliente_id.in_(scope.allowed_ids)`, `Estoque.usuario_id_cliente_admin == ca_id`). | **Confirmado** (padrão diferente, mesmo efeito) |
| Operações em massa sempre com `tenant_id` no WHERE | Não há evidência de update/delete em massa sem filtro de escopo nas APIs; listagens e mutations usam escopo. | **Confirmado** (recomenda-se manter em qualquer operação em massa futura) |

**Recomendação:** Em novos endpoints ou operações em massa, manter sempre filtro por `allowed_ids` ou por CA/tenant, e considerar um helper ou repositório que force o filtro de tenant/escopo para reduzir risco de esquecimento.

---

## CAMADA 5: Monitoramento e auditoria

| Guia | PDV Ibix | Status |
|------|----------------|--------|
| Log de auditoria com `tenant_id` | `audit_action(db, ..., tenant_id=...)` persiste em `AuditLog` (campo `tenant_id`). Estrutura pronta. Algumas chamadas passam `getattr(current_user, "tenant_id", None)` (correto). | **Confirmado** |
| Logs estruturados com tenant | `log_error`, `log_struct` aceitam `tenant_id`. Em exceções globais usa-se `request.state.tenant_id`, que hoje é cliente_id. | **Atenção** – valor de tenant nos logs pode estar errado |
| Rate limiting **por tenant** | Rate limit é por **IP** (`client_ip`), não por tenant (login, registro, API). Guia sugere `keyGenerator: (req) => req.tenantId`. | **Não implementado** (por tenant) |

**Recomendações:** (1) Ajustar `request.state.tenant_id` para o tenant real (ou usar outro nome, ex. `cliente_id`, e passar tenant_id para logs por outro canal). (2) Se quiser limitar abuso por organização, considerar rate limit por tenant (ex.: chave Redis `rate:tenant:{tenant_id}`).

---

## CAMADA 6: Segregação de arquivos

| Guia | PDV Ibix | Status |
|------|----------------|--------|
| Upload em pasta por tenant (`./uploads/tenant_X/`) | Fotos de estoque em `app/static/uploads/estoque_fotos/` (sem segmentação por tenant). Tabela `Estoque` tem `usuario_id_cliente_admin` (dono do dado), mas o path do arquivo não inclui tenant. | **Não implementado** |

**Risco:** Baixo se o controle de acesso aos registros (Estoque por CA) estiver sempre correto; em caso de bug, arquivos ficam no mesmo diretório. Para endurecer: salvar em subpasta por tenant ou por CA (ex.: `uploads/tenant_{id}/` ou `uploads/ca_{usuario_id_cliente_admin}/`).

---

## Checklist de segurança multi-tenant (conferido)

| Item | Situação no PDV |
|------|-----------------|
| Queries com filtro de tenant/escopo? | Sim: por `tenant_id` (billing, admin) ou por `cliente_id`/CA (vendas, notas, estoque, movimentações). |
| Middleware valida “tenant” em toda requisição? | Tenant não vem na requisição; é derivado do usuário. Subscription guard valida tenant ativo. |
| JWT contém tenant e é validado? | JWT não contém tenant; backend obtém tenant do usuário. Adequado para não confiar no frontend. |
| Todas as tabelas têm `tenant_id`? | Não. Tabelas operacionais usam `cliente_id`/CA; isolamento equivalente. |
| Índices compostos com `tenant_id` primeiro? | Sim onde existe `tenant_id` (subscriptions, billing_notificacoes, audit_log, usuarios, tenant_entitlements). |
| Nunca confiar no frontend para tenant? | Confirmado: tenant e escopo vêm do usuário no backend. |
| Auditoria com tenant? | Sim; garantir que todas as chamadas críticas a `audit_action` passem `tenant_id` correto (ex.: do usuário/CA). |

---

## Pontos críticos resumidos

1. **`request.state.tenant_id`** está recebendo **cliente_id** (estabelecimento), não o tenant da assinatura. Corrigir o preenchimento ou o nome e o uso em logs/auditoria para não misturar conceitos.
2. **Rate limit** é por IP; para “proteger por tenant” (um tenant não sobrecarregar os outros), implementar limite por tenant.
3. **Arquivos** (ex.: fotos estoque) não estão em pastas por tenant; considerar segregação por tenant/CA se quiser alinhar ao guia e facilitar backup/isolamento.
4. **Auditoria:** Revisar chamadas a `audit_action` para garantir que `tenant_id` seja sempre o tenant real (ex.: `resolve_tenant_pagador` ou `current_user.tenant_id` quando fizer sentido).

---

## Resumo final

- O guia é uma boa referência; o PDV não segue à letra (ex.: nem todas as tabelas com `tenant_id`, nem JWT com tenant, nem middleware que lê tenant do request), mas **o isolamento entre tenants está implementado** via escopo por cliente, CA e tenant onde aplicável.
- Para **evitar conflitos entre tenants**, o que mais importa já está atendido: filtros por escopo/CA em APIs operacionais, subscription guard por tenant, e auditoria com campo `tenant_id`. Os ajustes recomendados (nome/valor de `request.state.tenant_id`, rate limit por tenant, arquivos por tenant, auditoria consistente) aumentam a aderência ao guia e a clareza operacional sem mudar o modelo de dados atual.

Se quiser, posso detalhar um plano de alterações (por exemplo: correção de `request.state.tenant_id`, padrão de rate limit por tenant e estrutura de pastas de upload).
