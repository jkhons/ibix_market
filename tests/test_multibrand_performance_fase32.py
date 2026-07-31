"""Testes — desempenho multi-brand Fase 3.2."""
from unittest.mock import MagicMock, patch

from app.core.db_session_scope import apply_db_session_locals
from app.core.multibrand_metrics import record_http_request, status_class
from app.core.request_context import clear_request_context, get_request_context, set_request_context


def test_status_class_buckets():
    assert status_class(200) == "2xx"
    assert status_class(404) == "4xx"
    assert status_class(503) == "5xx"


def test_record_http_request_no_error():
    record_http_request(method="GET", brand_slug="ibix", status_code=200, duration_seconds=0.01)


def test_apply_db_session_locals_executes_set_local():
    db = MagicMock()
    with patch.dict("os.environ", {"DB_STATEMENT_TIMEOUT_MS": "15000", "RLS_ENABLED": "false"}):
        apply_db_session_locals(db)
    calls = [str(c[0][0]) for c in db.execute.call_args_list]
    assert any("statement_timeout" in c for c in calls)


def test_request_context_merge():
    clear_request_context()
    set_request_context(request_id="abc", brand_slug="ibix")
    set_request_context(tenant_id=42)
    ctx = get_request_context()
    assert ctx["request_id"] == "abc"
    assert ctx["brand_slug"] == "ibix"
    assert ctx["tenant_id"] == 42
    clear_request_context()


def test_open_db_session_applies_statement_timeout():
    from unittest.mock import MagicMock, patch

    from app.database.connection import open_db_session

    mock_session = MagicMock()
    with patch("app.database.connection.SessionLocal", return_value=mock_session):
        with patch.dict("os.environ", {"DB_STATEMENT_TIMEOUT_MS": "20000", "RLS_ENABLED": "false"}):
            db = open_db_session()
    assert db is mock_session
    calls = [str(c[0][0]) for c in mock_session.execute.call_args_list]
    assert any("statement_timeout" in c for c in calls)
