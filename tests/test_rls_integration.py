# Integração RLS real (Fase 9) — requer PostgreSQL de teste.
"""Rodar com: TEST_DATABASE_URL=postgresql://... pytest tests/test_rls_integration.py -m integration"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

TEST_URL = os.getenv("TEST_DATABASE_URL", "").strip()


def _resolve_integration_db_url() -> str:
    if TEST_URL:
        return TEST_URL
    if os.getenv("RLS_ENABLED", "").strip().lower() in ("1", "true", "yes", "on"):
        from app.database.connection import get_database_url

        return get_database_url()
    return ""


INTEGRATION_URL = _resolve_integration_db_url()


@pytest.fixture(scope="module")
def db_session():
    if not INTEGRATION_URL:
        pytest.skip("TEST_DATABASE_URL ou RLS_ENABLED+DB_* ausente")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(INTEGRATION_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


@pytest.mark.skipif(not INTEGRATION_URL, reason="DB integração indisponível")
def test_rls_policies_exist(db_session):
    from sqlalchemy import text

    count = db_session.execute(
        text("SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public'")
    ).scalar()
    assert count and count >= 20


@pytest.mark.skipif(not INTEGRATION_URL, reason="DB integração indisponível")
def test_set_local_tenant_context(db_session):
    from sqlalchemy import text

    from app.core.rls import apply_rls_session_locals

    db_session.rollback()
    apply_rls_session_locals(db_session, tenant_id=1, brand_id=1, bypass_rls=False)
    val = db_session.execute(
        text("SELECT current_setting('app.current_tenant', true)")
    ).scalar()
    assert val == "1"
    db_session.rollback()
