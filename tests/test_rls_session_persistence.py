"""RLS SET LOCAL deve sobreviver a commit (nova transação PostgreSQL)."""
import os

import pytest
from unittest.mock import MagicMock, patch

from app.core.db_session_scope import apply_db_session_locals
from app.core.request_context import clear_request_context, set_request_context


@patch("app.core.rls.rls_enabled", return_value=True)
def test_apply_db_session_locals_grava_pdv_rls_na_sessao(_mock_rls):
    clear_request_context()
    set_request_context(tenant_id=None, brand_id=1, bypass_rls=True)
    db = MagicMock()
    db.info = {}
    apply_db_session_locals(db)
    assert db.info["pdv_rls"]["bypass_rls"] is True
    assert db.info["pdv_rls"]["brand_id"] == 1
    assert db.info["pdv_session_locals_initialized"] is True


@patch("app.core.rls.rls_enabled", return_value=True)
def test_sync_rls_from_request_context_usa_apply_db_session_locals(_mock_rls):
    from app.core.rls import sync_rls_from_request_context

    clear_request_context()
    set_request_context(tenant_id=5, brand_id=1, bypass_rls=False)
    db = MagicMock()
    db.info = {}
    sync_rls_from_request_context(db)
    assert db.info["pdv_rls"]["tenant_id"] == 5
    assert db.info["pdv_rls"]["bypass_rls"] is False


@pytest.mark.skipif(
    os.getenv("RLS_ENABLED", "").strip().lower() not in ("1", "true", "yes", "on"),
    reason="requer RLS_ENABLED",
)
@patch("app.core.rls.rls_enabled", return_value=True)
def test_rls_bypass_sobrevive_commit_com_sessao_real(_mock_rls):
    from app.core.db_session_scope import setup_db_performance_hooks
    from app.database.connection import open_db_session
    from app.models.consumidor_marketplace import ConsumidorMarketplace
    from app.schemas.marketplace import ConsumidorResponse
    from sqlalchemy import text

    setup_db_performance_hooks()
    clear_request_context()
    set_request_context(brand_id=1, bypass_rls=True)
    db = open_db_session()
    try:
        row = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.ativo.is_(True)).first()
        if not row:
            pytest.skip("sem consumidor ativo no banco")
        db.commit()
        assert db.execute(text("SELECT current_setting('app.bypass_rls', true)")).scalar() == "on"
        ConsumidorResponse.model_validate(row)
    finally:
        db.close()
