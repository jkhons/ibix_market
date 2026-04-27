# Status da implementação – Plano RBAC, Tenants e Multitenancy (PDV Ibix)

Documento de referência do plano unificado: `rbac_tenants_e_multitenancy_pdv_unificado_d1040932.plan.md`.

## Nível 1 (concluído)

| Ação | Status | Onde |
|------|--------|------|
| Corrigir/renomear `request.state.tenant_id` | Concluído | `main.py`: uso de `request.state.cliente_id` (valor do JWT); handler de exceção usa `cliente_id` para correlação em log |
| Revisar `audit_action` com `tenant_id` consistente | Concluído | `precos_pdv.py`, `codigos_desconto.py` usam `resolve_tenant_pagador`; demais rotas usam `current_user.tenant_id` ou `tenant_id` do recurso |

## Nível 2 (concluído)

| Ação | Status | Onde |
|------|--------|------|
| Isolamento físico de arquivos | Concluído | `empresa.py`: logos em `uploads/empresa_logos/cliente_{cliente_id}/`; `estoque.py`: fotos em `uploads/estoque_fotos/ca_{ca_id}/`; compatibilidade com paths antigos |
| Rate limiting por tenant | Concluído | `main.py`: `tenant_rate_limit_middleware`; `rate_limiter.py`: `tenant_rate_limiter`; aplicado em rotas `/api/v1/` autenticadas; quando `tenant_id` é None não aplica limite por tenant |
| Testes de isolamento | Concluído | Cobertura pytest dedicada foi removida do repositório; isolamento permanece implementado em `app/` (escopo, APIs, cross-tenant 404) |

## Lacuna crítica Estoque (concluída)

| Ação | Status | Onde |
|------|--------|------|
| Filtrar Estoque quando `get_current_cliente_admin_id` retorna None | Concluído | `app/core/scope.py`: `get_ca_ids_for_cliente_ids`; `app/api/v1/estoque.py`: `_resolve_estoque_ca_ids` em todos os endpoints de listagem/leitura; Administrador filtra por clientes em `administrador_clientes`; Operador PDV retorna vazio |

## Outros itens do plano

- **Relacionamento Orcamento/Pedido:** Ajuste com `viewonly=True` em `Orcamento.convertido_em_pedido` para evitar erro de mapper (concluído).
- **Dados mockados:** Removidos do template CSV de onboarding e da suíte de testes legada (concluído).

## Nível 3 (opcional, não implementado)

- Middleware em dev para detectar queries sem escopo
- Repository pattern com `_apply_scope`
- Auditoria expandida (logs de acesso a rotas sensíveis)

## Migrações

Nenhuma migração nova foi necessária para as ações de nível 1 e 2. A evolução futura do escopo do Operador PDV (tabela `operador_pdv`) exigirá migração quando for implementada.
