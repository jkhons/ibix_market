# Login PDV com RLS ativo — usuário com tenant_id deve ser encontrado na autenticação.
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

TEST_URL = os.getenv("TEST_DATABASE_URL", "").strip()


def _resolve_db_url() -> str:
    if TEST_URL:
        return TEST_URL
    if os.getenv("RLS_ENABLED", "").strip().lower() in ("1", "true", "yes", "on"):
        from app.database.connection import get_database_url

        return get_database_url()
    return ""


DB_URL = _resolve_db_url()


@pytest.mark.skipif(not DB_URL, reason="DB integração indisponível")
def test_authenticate_user_visible_with_pre_auth_bypass():
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from app.core.rls import rls_enabled
    from app.database.connection import open_db_session
    from app.services.auth_service import AuthService

    if not rls_enabled():
        pytest.skip("RLS_ENABLED=false")

    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        conn.execute(text("SET LOCAL app.bypass_rls = 'on'"))
        row = conn.execute(
            text(
                """
                SELECT u.email
                FROM usuarios u
                JOIN roles r ON r.id = u.role_id
                WHERE lower(r.nome) = 'cliente administrador'
                  AND u.tenant_id IS NOT NULL
                  AND u.ativo = true
                LIMIT 1
                """
            )
        ).fetchone()
    if not row:
        pytest.skip("Nenhum CA com tenant_id no banco de teste")

    email = row[0]

    Session = sessionmaker(bind=engine)
    db_blocked = Session()
    try:
        from app.core.rls import apply_rls_session_locals

        apply_rls_session_locals(db_blocked, bypass_rls=False)
        found = db_blocked.query(
            __import__("app.models", fromlist=["Usuario"]).Usuario
        ).filter_by(email=email.strip().lower()).first()
        assert found is None, "RLS deve ocultar usuário tenant sem bypass na sessão normal"
    finally:
        db_blocked.close()

    db_pre = open_db_session(bypass_rls=True)
    try:
        found = AuthService.get_user_by_email(db_pre, email)
        assert found is not None, "get_db_pre_auth deve encontrar o usuário CA"
    finally:
        db_pre.close()


@pytest.mark.skipif(not DB_URL, reason="DB integração indisponível")
def test_populate_pdv_user_context_sets_tenant_with_rls():
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from app.core.db_session_scope import apply_db_session_locals
    from app.core.request_context import clear_request_context, get_request_context, populate_pdv_user_context
    from app.core.rls import rls_enabled
    from app.models import Usuario

    if not rls_enabled():
        pytest.skip("RLS_ENABLED=false")

    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        conn.execute(text("SET LOCAL app.bypass_rls = 'on'"))
        row = conn.execute(
            text(
                "SELECT id FROM usuarios WHERE tenant_id IS NOT NULL AND ativo = true LIMIT 1"
            )
        ).fetchone()
    if not row:
        pytest.skip("Sem usuário tenant no banco")

    clear_request_context()
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        populate_pdv_user_context(db, row[0])
        ctx = get_request_context()
        assert ctx.get("tenant_id") is not None
        apply_db_session_locals(db)
        assert db.query(Usuario).filter(Usuario.id == row[0]).first() is not None
    finally:
        db.close()
        clear_request_context()
