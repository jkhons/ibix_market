# PDV Ibix — Escopo de sessão DB: statement_timeout SET LOCAL (Fase 3.2)
"""SET LOCAL é compatível com PgBouncer transaction mode (não vaza entre tenants)."""
from __future__ import annotations

import os
import time
from typing import Any, Optional

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.logging import log_warning
from app.core.request_context import get_request_context
from app.database.connection import engine


def _statement_timeout_ms() -> Optional[int]:
    raw = (os.getenv("DB_STATEMENT_TIMEOUT_MS") or "30000").strip()
    if not raw or raw.lower() in ("0", "off", "false", "none"):
        return None
    try:
        return max(1, int(raw))
    except ValueError:
        return 30000


def _slow_query_threshold_ms() -> int:
    raw = (os.getenv("DB_SLOW_QUERY_MS") or "500").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 500


def apply_db_session_locals(
    db: Session,
    *,
    tenant_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    bypass_rls: Optional[bool] = None,
) -> None:
    """Aplica SET LOCAL no início da transação da request."""
    timeout_ms = _statement_timeout_ms()
    if timeout_ms is not None:
        db.execute(text(f"SET LOCAL statement_timeout = '{timeout_ms}ms'"))

    from app.core.rls import apply_rls_session_locals, rls_enabled

    if rls_enabled():
        ctx = get_request_context()
        effective_tenant = tenant_id if tenant_id is not None else ctx.get("tenant_id")
        effective_brand = brand_id if brand_id is not None else ctx.get("brand_id")
        if bypass_rls is not None:
            effective_bypass = bypass_rls
        else:
            effective_bypass = bool(ctx.get("bypass_rls"))

        db.info["pdv_rls"] = {
            "tenant_id": effective_tenant,
            "brand_id": effective_brand,
            "bypass_rls": effective_bypass,
        }
        apply_rls_session_locals(
            db,
            tenant_id=effective_tenant,
            brand_id=effective_brand,
            bypass_rls=effective_bypass,
        )

    db.info["pdv_session_locals_initialized"] = True


def _reapply_db_session_locals(session: Session, connection=None) -> None:
    """Reaplica SET LOCAL após commit (nova transação perde SET LOCAL no PostgreSQL)."""
    timeout_ms = _statement_timeout_ms()

    def _exec(sql, params=None):
        if connection is not None:
            if params:
                connection.execute(sql, params)
            else:
                connection.execute(sql)
        else:
            session.execute(sql, params or {})

    if timeout_ms is not None:
        _exec(text(f"SET LOCAL statement_timeout = '{timeout_ms}ms'"))

    from app.core.rls import apply_rls_session_locals, rls_enabled

    if not rls_enabled():
        return
    stored = session.info.get("pdv_rls")
    if stored:
        if connection is not None:
            bypass = stored.get("bypass_rls")
            tenant_id = stored.get("tenant_id")
            brand_id = stored.get("brand_id")
            connection.execute(
                text("SET LOCAL app.bypass_rls = :val"),
                {"val": "on" if bypass else "off"},
            )
            connection.execute(
                text("SET LOCAL app.current_tenant = :val"),
                {"val": str(tenant_id) if tenant_id is not None else ""},
            )
            connection.execute(
                text("SET LOCAL app.current_brand = :val"),
                {"val": str(brand_id) if brand_id is not None else ""},
            )
        else:
            apply_rls_session_locals(session, **stored)
        return
    if connection is None:
        from app.core.rls import sync_rls_from_request_context

        sync_rls_from_request_context(session)


def _register_session_after_begin_listener() -> None:
    @event.listens_for(Session, "after_begin")
    def _pdv_session_after_begin(session, transaction, connection):  # noqa: ARG001
        if not session.info.get("pdv_session_locals_initialized"):
            return
        _reapply_db_session_locals(session, connection=connection)


def _register_slow_query_listener(db_engine: Engine) -> None:
    threshold = _slow_query_threshold_ms()

    @event.listens_for(db_engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        if context is not None:
            context._pdv_query_start = time.perf_counter()

    @event.listens_for(db_engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        if context is None or not hasattr(context, "_pdv_query_start"):
            return
        elapsed_ms = (time.perf_counter() - context._pdv_query_start) * 1000.0
        if elapsed_ms < threshold:
            return
        ctx = get_request_context()
        stmt_preview = (statement or "").replace("\n", " ").strip()[:200]
        log_warning(
            f"slow_query elapsed_ms={elapsed_ms:.1f} threshold_ms={threshold} "
            f"brand_slug={ctx.get('brand_slug')} tenant_id={ctx.get('tenant_id')} "
            f"user_id={ctx.get('user_id')} request_id={ctx.get('request_id')} "
            f"stmt={stmt_preview!r}"
        )


_listeners_registered = False


def setup_db_performance_hooks() -> None:
    global _listeners_registered
    if _listeners_registered:
        return
    _register_slow_query_listener(engine)
    _register_session_after_begin_listener()
    _listeners_registered = True
