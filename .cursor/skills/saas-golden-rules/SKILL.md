---
name: saas-golden-rules
description: Enforces golden rules for the PDV Ibix SaaS system. Never use fallbacks for submitting data, always create parameters and UI controls in the front, strictly follow RBAC/permissions/tenants. Use when implementing features, APIs, frontend, or reviewing code in this multi-tenant SaaS.
---

# Regras de Ouro — Sistema SaaS PDV Ibix

Este sistema é **SaaS real em produção**. Segue padrões de grandes players. As regras abaixo são obrigatórias.

## 1. Nunca usar fallback para subir informações

**❌ Proibido:**
- Retornar valor alternativo (`None`, string vazia, 0, lista vazia) quando o dado obrigatório não existe
- Usar "primeira empresa do escopo", "primeiro cliente" ou similar para preencher campos obrigatórios
- Mascarar erros com valores padrão (ex.: `if config else 24` para evitar falha)

**✅ Obrigatório:**
- Se dado obrigatório não existir → **lançar erro explícito** (HTTP 4xx/5xx ou exceção)
- Falhar de forma visível e rastreável
- **Exceção:** apenas onde o mapa/contrato da API documentar explicitamente valor padrão permitido

**Exemplos:**
```python
# ❌ Errado
empresa = get_empresa_fiscal(db, user) or db.query(Cliente).first()

# ✅ Correto
empresa = get_empresa_fiscal_empresa(db, user)
if not empresa:
    raise HTTPException(400, "Empresa Fiscal obrigatória. Configure em /fiscal/empresa")
```

## 2. Sempre criar parâmetros e ajustes no front

**❌ Proibido:**
- Dados hardcoded no frontend (arrays, valores fixos, listas de opções em JS/HTML)
- Fallbacks hardcoded (ex.: `if config else 24`)
- Breadcrumbs, sidebars ou valores duplicados no código frontend

**✅ Obrigatório:**
- Criar tabela/entidade no banco quando o dado for necessário
- Expor via API REST e consumir no frontend
- Usar `window.authenticatedFetch` para chamadas à API (inclui token e escopo)
- Sugerir cadastro/parâmetro no banco se ainda não existir; aguardar aprovação antes de implementar alternativa

**Fluxo obrigatório:**
1. Identificar necessidade de dados
2. Verificar se já existe tabela/API
3. Se não existir → **SUGERIR** criação e **AGUARDAR APROVAÇÃO**
4. Se aprovado → migração + endpoint + consumo no front

## 3. Seguir rigorosamente RBAC, acesso e tenants

**Hierarquia obrigatória (ver `MAPA_RBAC.md`):**
- **Superadministrador** → **Administrador** → **Cliente Administrador** → **Técnico** | **Subcliente**

**Regras:**
- **Isolamento Subcliente:** Subcliente não vê dados de outro Subcliente; escopo obrigatório por `cliente_id`
- **Cliente Administrador** não acessa `/usuarios` nem `/configuracoes` (apenas Superadmin e Admin)
- **Empresa Fiscal obrigatória:** operações fiscais usam exclusivamente a Empresa Fiscal do CA (`get_empresa_fiscal_empresa` / `get_empresa_fiscal_cliente_id`)
- **Produto do estabelecimento (`produtos_cliente`):** **`cliente_id` é obrigatório** (NOT NULL no modelo). Esse `cliente_id` é o cadastro do **CA / empresa fiscal** no domínio atual (isolamento entre tenants e respeito a CNPJs distintos). Não tratar produto de catálogo sem estabelecimento; no futuro, se um tenant tiver várias empresas fiscais, cada uma continua representada pelo seu `cliente_id` correspondente.
- **Escopo por tenant:** APIs devem filtrar por `ClienteScope.allowed_ids` quando `must_filter_by_cliente()`
- Verificar `require_permission`, `forbid_cliente_access` e `get_cliente_scope_dep` em todas as rotas

**Novos endpoints:**
- Usar `require_permission("modulo:acao")` para ações distintas
- Garantir que a permissão exista em `permissoes` (migration/seed) e esteja atribuída às roles corretas

## 4. Validade jurídica — Nunca publicar informação sem fluxo real

**❌ Proibido:**
- Exibir confirmação de venda/compra sem pagamento efetivamente confirmado no sistema
- Mostrar mensagens como "Compra finalizada" ou "Pagamento aprovado" quando o status real for pendente
- Usar fallbacks que exibam sucesso quando o fluxo real (gateway, webhook, reconciliação) não confirmou

**✅ Obrigatório:**
- Confirmar pagamento apenas quando `status_pagamento = "pago"` (ou equivalente no domínio)
- Em páginas de retorno de gateway, validar estado real antes de exibir qualquer confirmação
- Em caso de dúvida, redirecionar para "aguardando" ou "não concluído" em vez de assumir sucesso

**Risco:** Confirmação indevida de venda sem pagamento gera responsabilidade jurídica para a plataforma.

## 5. Contexto SaaS — Referências

- **Fonte única de verdade:** `MAPA_SISTEMA/` (MAPA_DO_SISTEMA, MAPA_DE_REGRAS, MAPA_RBAC, MAPA_DE_API)
- **Regras detalhadas:** `MAPA_DE_REGRAS.md` — seção 0 (Regras obrigatórias para Cursor/IA)
- **RBAC e roles:** `MAPA_RBAC.md` — hierarquia, escopo, rotas por role

## 5.1 Marketing Vitrine — cards da home (`/loja`)

- **Onde se configura:** exclusivamente **`/admin/marketing-vitrine`**, pelo **Superadministrador** (`require_superadmin` nas APIs `/api/v1/marketing-vitrine/*`).
- **O que entra:** `marketing_vitrine_config` + `marketing_vitrine_cards` (destaques, ofertas da semana, cabeçalho de ofertas). Não criar outra tela de cadastro de cards nem lista fixa no código como fonte editorial.
- **Documentação:** `MAPA_DE_API.md` § 19 (regra de governança), `MAPA_DO_SISTEMA.md` § 12.

## Checklist rápido (antes de implementar)

- [ ] Dado obrigatório ausente → lanço erro explícito (não uso fallback)?
- [ ] Dados dinâmicos vêm de API/banco (não hardcoded no front)?
- [ ] Verifiquei permissões e escopo tenant para a rota/API?
- [ ] Catálogo `produtos_cliente`: todo produto com `cliente_id` (CA/empresa fiscal), sem “produto global” sem estabelecimento?
- [ ] Consultei o mapa relevante para consistência?
- [ ] Confirmações de venda/pagamento refletem o fluxo real (não publico sucesso sem prova)?
- [ ] Cards de marketing da vitrine: alteração só via `/admin/marketing-vitrine` (Superadmin), não hardcode de cards?
