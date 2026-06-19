# AGENTS — PDV Ibix (instruções para IA)

## Fluxo obrigatório

1. Abra **[MAPA_SISTEMA/INDICE.md](MAPA_SISTEMA/INDICE.md)** e escolha **um** mapa para a tarefa.
2. Leia **[MAPA_SISTEMA/MAPA_DE_REGRAS.md](MAPA_SISTEMA/MAPA_DE_REGRAS.md)** § 0 antes de implementar.
3. Consulte o mapa de domínio (API, RBAC, pagamento, etc.) — **não** carregue `MAPA_DO_SISTEMA.md` inteiro; use o sumário e a § indicada no índice.
4. Tarefas multi-brand, RBAC/tenant, migração ou segurança por domínio: leia **[MAPA_MULTIBRAND.md](MAPA_SISTEMA/MAPA_MULTIBRAND.md)** e as regras em **`.cursor/rules/`** aplicáveis.
5. Se a mudança for estrutural, proponha atualização objetiva do mapa correspondente.

## Estrutura da documentação

| Camada | Arquivos |
|--------|----------|
| **Núcleo** (6) | `MAPA_DO_SISTEMA`, `MAPA_DE_API`, `MAPA_DE_REGRAS`, `MAPA_RBAC`, `MAPA_PAGAMENTO`, `MAPA_FATURAMENTO` |
| **Satélites** (8) | `MAPA_MULTIBRAND`, `MAPA_MODELO_PAGAMENTO_MARKETPLACE`, `MAPA_Frete_Transporte`, `MAPA_DEPLOY_SERVICOS`, `MAPA_GOOGLE_OAUTH_VITRINE`, `MAPA_PADRONIZACAO_PDV_VITRINE`, `REPOSITORIOS_GITHUB`, `INDICE` |
| **Planos** | `.cursor/plans/` (ex.: app mobile marketplace, multi-brand) |
| **Regras Cursor** | `.cursor/rules/` — multibrand, modulo-gating, tenant-rls, conflito-dados, seguranca-dominio |

Detalhes: [MAPA_SISTEMA/INDICE.md](MAPA_SISTEMA/INDICE.md).

## Regras-síntese (não negociáveis)

1. **Sem fallback** — dado obrigatório ausente → erro explícito (4xx/5xx), não valor substituto.
2. **Sem hardcode no front** — dados dinâmicos via API/banco; usar `base.html` e `authenticatedFetch`; branding via `{{ brand.* }}` (ver `.cursor/rules/multibrand-no-hardcode.mdc`).
3. **RBAC e tenant** — hierarquia Superadmin → Admin → CA → Técnico/Subcliente; escopo por `cliente_id`/tenant; RLS + `tenant_id`/`brand_id` (ver `.cursor/rules/tenant-rls.mdc`).
4. **Validade jurídica** — não exibir sucesso de pagamento/venda sem confirmação real (gateway/webhook/reconciliação).
5. **Multi-brand** — gating de módulo por marca (403 sem fallback); Host via `brand_domains` (ver [MAPA_MULTIBRAND.md](MAPA_SISTEMA/MAPA_MULTIBRAND.md) e `.cursor/rules/modulo-gating.mdc`).

Skill detalhada: [.cursor/skills/saas-golden-rules/SKILL.md](.cursor/skills/saas-golden-rules/SKILL.md).

## Palavras-chave → mapa

Use a tabela em `MAPA_SISTEMA/INDICE.md` (seção «Palavras-chave para busca»). Exemplos:

- API / endpoint → `MAPA_DE_API.md`
- Permissão / role → `MAPA_RBAC.md`
- Assinatura / billing / Recebíveis → `MAPA_PAGAMENTO.md`
- Marketplace / repasse → `MAPA_MODELO_PAGAMENTO_MARKETPLACE.md` + `MAPA_DO_SISTEMA.md` § 12
- Multi-brand, brand_id, Solumática, gating → `MAPA_MULTIBRAND.md` + `MAPA_RBAC.md` § 0.13
- NF-e XML / SEFAZ → `MAPA_FATURAMENTO.md`

## App mobile

Plano: [.cursor/plans/plano_app_mobile_marketplace.plan.md](.cursor/plans/plano_app_mobile_marketplace.plan.md)  
Contexto do app: [mobile_marketplace/AGENTS.md](mobile_marketplace/AGENTS.md)
