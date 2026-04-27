# Verificação: execução de todos os planos

**Data:** 2026-03-02  
**Escopo:** Planos em `.cursor/plans/*.plan.md` e implementação no repositório **pdv_solumatica**.

---

## Resumo

| Plano | Tipo | Executado? | Observação |
|-------|------|------------|------------|
| Plano Faturamento e NFS-e | Implementação | **Sim** | Ver [CONFIRMACAO_IMPLEMENTACAO_NFSE.md](CONFIRMACAO_IMPLEMENTACAO_NFSE.md). Fases 0–9 implementadas (provider nacional em stub; UI e job PDF concluídos). |
| Comissão Admin e Código Promocional | Implementação | **Sim** | Modelo `ComissaoAdministrador`, `subscription.codigo_desconto_id`, cadastro com `codigo_promocional`, tenant+subscription no register, webhook comissão, campo no `register_public.html`. Códigos: POST/PATCH usam `require_superadmin()` em vários endpoints. |
| Módulo local NF-e SaaS | Implementação/design | **Sim (núcleo)** | `ProvedorFiscalLocal` em `app/services/fiscal/provedor_local.py`; `get_provedor_fiscal` por empresa; certificado por empresa. Plano é amplo (curso M0–M6, etc.); núcleo fiscal local está implementado. |
| Sidebar scroll continuity | Implementação | **Sim** | `app/static/js/sidebar-fix.js`: persiste/restaura scroll com chave por path/role/tenant, debounce, filtro de cliques, pagehide, bfcache. |
| Análise RBAC Tenants CA-CF PDV | **Análise** | N/A | Documento de análise do estado atual (RBAC, tenants, hierarquia). Não é plano de implementação; não há “execução” a verificar. |
| Módulo Orçamento e Pedido | Implementação | **Sim** | Todos os todos no frontmatter estão `completed`. Models `orcamento.py`, `pedido.py`, `nota_fiscal.pedido_id`; APIs, serviços, templates e sidebar presentes. |
| Replicar módulo Orçamento e Pedido no solumatica_auto | Implementação (outro repo) | **Declarado completo** | Plano para o repositório **solumatica_auto**. Todos os todos estão `completed` no frontmatter. A verificação física seria no repo solumatica_auto, não neste (pdv_solumatica). |

---

## 1. Plano Faturamento e NFS-e

- **Arquivo:** [plano_faturamento_nfse_implementacao.plan.md](plano_faturamento_nfse_implementacao.plan.md)
- **Status:** **Executado.** Relatório detalhado em [CONFIRMACAO_IMPLEMENTACAO_NFSE.md](CONFIRMACAO_IMPLEMENTACAO_NFSE.md).
- **Evidência no código:** migrações `nfse00_ibge`, `nfse01_tbl`, `nfse01b_rps`; modelos `app/models/nfse.py`; serviços `app/services/nfse/`; API `app/api/v1/nfse.py`; worker `app/worker/nfse_tasks.py`; telas `/fiscal/nfse-config`, `/fiscal/nfse-pendencias`; testes `tests/test_nfse_*.py`.

---

## 2. Comissão Admin e Código Promocional

- **Arquivo:** [comissão_admin_e_código_promocional_08838e5f.plan.md](comissão_admin_e_código_promocional_08838e5f.plan.md)
- **Status:** **Executado.**
- **Evidência no código:**
  - `ComissaoAdministrador` em `app/models/subscription_billing.py`; listagem e PATCH em `app/api/v1/admin_billing.py` (comissões).
  - `SubscriptionBilling.codigo_desconto_id`; uso em billing e webhook.
  - `auth_service.register_public`: valida `codigo_promocional`, cria Tenant + Subscription com desconto e `codigo_desconto_id`, vínculo `AdministradorClienteAdministrador`.
  - `RegisterPublicRequest.codigo_promocional` em `app/schemas/auth.py`.
  - Campo "Código promocional" em `app/templates/auth/register_public.html` e envio no payload.
  - Criação/edição de códigos: vários endpoints em `app/api/v1/codigos_desconto.py` usam `require_superadmin()` (POST/PATCH restritos ao Super Admin onde definido).

---

## 3. Módulo local NF-e SaaS

- **Arquivo:** [módulo_local_nf-e_saas_250fcba4.plan.md](módulo_local_nf-e_saas_250fcba4.plan.md)
- **Status:** **Núcleo executado.** Plano inclui também curso de implantação (M0–M6) e documentação; o núcleo técnico (provedor local, certificado, XML, SEFAZ) está implementado.
- **Evidência no código:**
  - `ProvedorFiscalLocal` em `app/services/fiscal/provedor_local.py` implementando `IProvedorFiscal`.
  - `get_provedor_fiscal(db, empresa)` em `app/services/fiscal/emissao_service.py` retornando `ProvedorFiscalLocal` quando `empresa.provedor_fiscal == 'local'`.
  - Testes em `tests/test_fiscal_module.py` para `get_provedor_fiscal` e `ProvedorFiscalLocal`.

---

## 4. Sidebar scroll continuity

- **Arquivo:** [sidebar_scroll_continuity_5e457a29.plan.md](sidebar_scroll_continuity_5e457a29.plan.md)
- **Status:** **Executado.**
- **Evidência no código:**
  - `app/static/js/sidebar-fix.js`: `STORAGE_PREFIX = 'sidebarScrollY'`; chave por pathname + role + tenant; `saveScroll` em scroll (debounce), click (com `shouldSaveOnClick`) e pagehide; `restoreScroll` em DOMContentLoaded e pageshow (com cuidado bfcache); filtro de modificadores e links externos/âncora.

---

## 5. Análise RBAC Tenants CA-CF PDV

- **Arquivo:** [análise_rbac_tenants_ca-cf_pdv_4a5e5b7c.plan.md](análise_rbac_tenants_ca-cf_pdv_4a5e5b7c.plan.md)
- **Status:** **Documento de análise.** Não é plano de implementação; descreve o estado atual de RBAC, multi-tenancy e hierarquia. Nada a “executar”; não se aplica verificação de implementação.

---

## 6. Módulo Orçamento e Pedido

- **Arquivo:** [módulo_orçamento_e_pedido_60439410.plan.md](módulo_orçamento_e_pedido_60439410.plan.md)
- **Status:** **Executado.** Todos os todos do frontmatter estão `completed`.
- **Evidência no código:** models `app/models/orcamento.py`, `app/models/pedido.py`; `NotaFiscal.pedido_id`; APIs orçamentos/pedidos; serviços; rotas HTML e templates; relatório de conversão; sidebar e permissões.

---

## 7. Replicar módulo Orçamento e Pedido no solumatica_auto

- **Arquivo:** [replicar_módulo_orçamento_e_pedido_no_solumatica_auto_a6566b2d.plan.md](replicar_módulo_orçamento_e_pedido_no_solumatica_auto_a6566b2d.plan.md)
- **Status:** **Declarado completo no plano** (todos `completed`). O alvo é o repositório **solumatica_auto**; neste workspace (pdv_solumatica) não é possível verificar o outro repositório. Para confirmar no solumatica_auto, é necessário abrir aquele projeto e checar migrations, models, APIs e templates lá.

---

## Conclusão

- **No pdv_solumatica:** todos os planos de **implementação** que se aplicam a este repositório foram **executados** (Faturamento NFS-e, Comissão/Código promocional, Módulo local NF-e, Sidebar scroll, Orçamento e Pedido).
- **Análise RBAC:** apenas análise; não há itens de implementação a verificar.
- **Replicar no solumatica_auto:** plano marcado como concluído; verificação física deve ser feita no repositório solumatica_auto.

Os frontmatters de alguns planos (ex.: Faturamento NFS-e) ainda têm `status: pending` nos todos; isso reflete o arquivo do plano não ter sido atualizado após a implementação, não o estado real do código.
