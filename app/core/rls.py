# PDV Ibix — Row-Level Security (Fase 6 / Fase 3 PostgreSQL)
"""SET LOCAL app.current_* por request; bypass para Superadministrador."""
from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.request_context import get_request_context

# Tabelas excluídas da política tenant_id (tratamento especial ou globais de plataforma).
RLS_SKIP_TENANT_TABLES = frozenset(
    {
        "alembic_version",
    }
)

# Política tenant_id: índice simples sobre coluna indexada (sem subquery).
RLS_TENANT_POLICY = """
CREATE POLICY rls_{table}_tenant ON {table}
  AS PERMISSIVE FOR ALL TO PUBLIC
  USING (
    current_setting('app.bypass_rls', true) = 'on'
    OR (
      current_setting('app.current_tenant', true) <> ''
      AND tenant_id IS NOT DISTINCT FROM NULLIF(current_setting('app.current_tenant', true), '')::integer
    )
  )
  WITH CHECK (
    current_setting('app.bypass_rls', true) = 'on'
    OR (
      current_setting('app.current_tenant', true) <> ''
      AND tenant_id IS NOT DISTINCT FROM NULLIF(current_setting('app.current_tenant', true), '')::integer
    )
  )
"""

RLS_TENANTS_BRAND_POLICY = """
CREATE POLICY rls_tenants_scope ON tenants
  AS PERMISSIVE FOR ALL TO PUBLIC
  USING (
    current_setting('app.bypass_rls', true) = 'on'
    OR (
      current_setting('app.current_tenant', true) <> ''
      AND id = NULLIF(current_setting('app.current_tenant', true), '')::integer
    )
    OR (
      current_setting('app.current_brand', true) <> ''
      AND brand_id = NULLIF(current_setting('app.current_brand', true), '')::integer
    )
  )
  WITH CHECK (
    current_setting('app.bypass_rls', true) = 'on'
    OR (
      current_setting('app.current_tenant', true) <> ''
      AND id = NULLIF(current_setting('app.current_tenant', true), '')::integer
    )
    OR (
      current_setting('app.current_brand', true) <> ''
      AND brand_id = NULLIF(current_setting('app.current_brand', true), '')::integer
    )
  )
"""


def rls_enabled() -> bool:
    return os.getenv("RLS_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")


def apply_rls_session_locals(
    db: Session,
    *,
    tenant_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    bypass_rls: bool = False,
) -> None:
    """SET LOCAL — compatível com PgBouncer transaction mode."""
    if not rls_enabled():
        return
    db.execute(
        text("SET LOCAL app.bypass_rls = :val"),
        {"val": "on" if bypass_rls else "off"},
    )
    db.execute(
        text("SET LOCAL app.current_tenant = :val"),
        {"val": str(tenant_id) if tenant_id is not None else ""},
    )
    db.execute(
        text("SET LOCAL app.current_brand = :val"),
        {"val": str(brand_id) if brand_id is not None else ""},
    )


def sync_rls_from_request_context(db: Session) -> None:
    """Reaplica RLS a partir do ContextVar (após auth/brand middleware)."""
    from app.core.db_session_scope import apply_db_session_locals

    apply_db_session_locals(db)


def resolve_rls_bypass_for_role(role_nome: Optional[str]) -> bool:
    return (role_nome or "").strip() == "Superadministrador"


def update_rls_context_from_user(user, *, brand_id: Optional[int] = None) -> None:
    """Atualiza ContextVar para RLS após carregar usuário."""
    from app.core.request_context import update_request_context

    tenant_id = getattr(user, "tenant_id", None)
    role_nome = user.role.nome if getattr(user, "role", None) else None
    update_request_context(
        user_id=getattr(user, "id", None),
        tenant_id=tenant_id,
        brand_id=brand_id,
        bypass_rls=resolve_rls_bypass_for_role(role_nome),
    )


__all__ = [
    "RLS_SKIP_TENANT_TABLES",
    "RLS_TENANT_POLICY",
    "RLS_TENANTS_BRAND_POLICY",
    "apply_rls_session_locals",
    "resolve_rls_bypass_for_role",
    "rls_enabled",
    "sync_rls_from_request_context",
    "update_rls_context_from_user",
]
