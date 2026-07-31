# Fase 9 — testes enterprise (startup, secrets, worker session, lifecycle)
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from app.core.enterprise_checks import run_enterprise_startup_checks
from app.core.secrets_provider import get_secret, secrets_backend
from app.core.structured_log_context import RequestContextLogFilter
from app.worker.db_task import worker_db_session


def test_secrets_backend_default_env():
    assert secrets_backend() == "env"


def test_get_secret_from_env(monkeypatch):
    monkeypatch.setenv("TEST_SECRET_X", "valor")
    assert get_secret("TEST_SECRET_X") == "valor"


def test_get_secret_required_raises(monkeypatch):
    monkeypatch.delenv("MISSING_SECRET_X", raising=False)
    with pytest.raises(RuntimeError, match="MISSING_SECRET_X"):
        get_secret("MISSING_SECRET_X", required=True)


def test_enterprise_checks_warn_when_rls_off(monkeypatch):
    monkeypatch.delenv("RLS_ENABLED", raising=False)
    monkeypatch.setenv("ENV", "development")
    result = run_enterprise_startup_checks(strict=False)
    assert any("RLS_ENABLED=false" in w for w in result["warnings"])


def test_enterprise_checks_error_rls_with_postgres_user(monkeypatch):
    monkeypatch.setenv("RLS_ENABLED", "true")
    monkeypatch.setenv("DB_USER", "postgres")
    monkeypatch.setenv("ENV", "development")
    result = run_enterprise_startup_checks(strict=False)
    assert any("BYPASSRLS" in e or "postgres" in e for e in result["errors"])


@patch("app.core.rls.rls_enabled", return_value=True)
@patch("app.database.connection.open_db_session")
def test_worker_db_session_platform_bypass(mock_open, _rls):
    mock_db = MagicMock()
    mock_open.return_value = mock_db
    with worker_db_session() as db:
        assert db is mock_db
    mock_open.assert_called_once_with(tenant_id=None, brand_id=None, bypass_rls=True)
    mock_db.close.assert_called_once()


def test_structured_log_filter_adds_context():
    from app.core.request_context import clear_request_context, set_request_context

    clear_request_context()
    set_request_context(request_id="abc", tenant_id=7, brand_id=2)
    filt = RequestContextLogFilter()
    record = MagicMock()
    record.getMessage = MagicMock(return_value="evento teste")
    record.msg = "evento teste"
    record.args = ()
    assert filt.filter(record) is True
    assert "request_id=abc" in record.msg
    assert "tenant_id=7" in record.msg
    clear_request_context()


def test_tenant_lifecycle_suspend_requires_tenant(monkeypatch):
    from app.services.tenant_lifecycle_service import suspender_tenant

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(ValueError, match="TENANT_NOT_FOUND"):
        suspender_tenant(db, 999)
