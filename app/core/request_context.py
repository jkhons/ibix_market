# PDV Ibix — Contexto da requisição para logs/métricas (Fase 3.2 multi-brand)
"""ContextVar propagado no worker; preenchido no middleware e atualizado após auth."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Optional

_request_ctx: ContextVar[dict[str, Any]] = ContextVar("pdv_request_context", default={})


def get_request_context() -> dict[str, Any]:
    return dict(_request_ctx.get())


def set_request_context(**fields: Any) -> None:
    data = dict(_request_ctx.get())
    for key, value in fields.items():
        if value is not None:
            data[key] = value
    _request_ctx.set(data)


def update_request_context(**fields: Any) -> None:
    set_request_context(**fields)


def clear_request_context() -> None:
    _request_ctx.set({})


def context_brand_slug(default: str = "unknown") -> str:
    return str(get_request_context().get("brand_slug") or default)


def context_tenant_id() -> Optional[int]:
    raw = get_request_context().get("tenant_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def populate_pdv_user_context(db, user_id: int) -> None:
    """Preenche user_id/tenant_id/bypass RLS no contexto (rotas autenticadas por cookie)."""
    from sqlalchemy.orm import joinedload

    from app.core.rls import (
        apply_rls_session_locals,
        resolve_rls_bypass_for_role,
        rls_enabled,
        sync_rls_from_request_context,
    )
    from app.core.scope import resolve_tenant_pagador
    from app.models import Usuario

    update_request_context(user_id=user_id)
    # Com RLS ativo, usuarios com tenant_id ficam invisíveis até o tenant ser conhecido.
    if rls_enabled():
        apply_rls_session_locals(db, bypass_rls=True)
    user = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == user_id).first()
    if not user:
        return
    tenant_id = resolve_tenant_pagador(db, user.id, user.role.nome if user.role else None)
    role_nome = user.role.nome if user.role else None
    update_request_context(
        tenant_id=tenant_id,
        bypass_rls=resolve_rls_bypass_for_role(role_nome),
    )
    sync_rls_from_request_context(db)
