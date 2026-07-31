# PDV Ibix — Checagens enterprise no startup (Fase 9)
"""Valida RLS, role DB e segredos antes de servir tráfego em produção."""
from __future__ import annotations

import os
from typing import List

from sqlalchemy import text

from app.core.logging import logger
from app.core.rls import rls_enabled


def _is_production() -> bool:
    return os.getenv("ENV", "").strip().lower() == "production"


def _check_rls_db_role(warnings: List[str], errors: List[str]) -> None:
    if not rls_enabled():
        warnings.append("RLS_ENABLED=false — políticas PostgreSQL não filtram (aceitável em dev/homolog).")
        return

    db_user = (os.getenv("DB_USER") or "").strip().lower()
    if db_user in ("postgres", "root", ""):
        errors.append(
            f"RLS_ENABLED=true mas DB_USER={db_user!r} — use role pdv_app sem BYPASSRLS "
            "(scripts/sql/create_pdv_app_role.sql)."
        )
        return

    try:
        from app.database.connection import open_db_session

        db = open_db_session(bypass_rls=True)
        try:
            row = db.execute(
                text(
                    "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
                )
            ).mappings().first()
            if row and (row.get("rolsuper") or row.get("rolbypassrls")):
                errors.append(
                    f"Role DB {row.get('rolname')} tem superuser ou BYPASSRLS — RLS inefetivo."
                )
        finally:
            db.close()
    except Exception as exc:
        warnings.append(f"Não foi possível verificar role PostgreSQL: {exc}")


def _check_secrets_production(warnings: List[str], errors: List[str]) -> None:
    if not _is_production():
        return
    for key in ("PAYMENT_CREDENTIALS_SECRET", "PAYMENT_CREDENTIALS_PASSWORD"):
        if os.getenv(key, "").strip():
            return
    errors.append(
        "Produção sem PAYMENT_CREDENTIALS_SECRET/PASSWORD — segredos billing não cifrados."
    )


def run_enterprise_startup_checks(*, strict: bool | None = None) -> dict:
    """
    Executa checagens Fase 9. strict=True em produção falha o processo se houver errors.
    """
    if strict is None:
        strict = _is_production() and os.getenv("ENTERPRISE_STRICT_STARTUP", "false").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    warnings: List[str] = []
    errors: List[str] = []

    _check_rls_db_role(warnings, errors)
    _check_secrets_production(warnings, errors)

    for w in warnings:
        logger.warning(f"enterprise_check: {w}")
    for e in errors:
        logger.error(f"enterprise_check: {e}")

    if strict and errors:
        raise RuntimeError(
            "Checagens enterprise falharam: " + "; ".join(errors)
        )

    return {"warnings": warnings, "errors": errors, "strict": strict}
