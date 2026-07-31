"""Testes — isolamento multi-tenant / multi-brand (Fase 6)."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.rls import (
    RLS_TENANT_POLICY,
    apply_rls_session_locals,
    resolve_rls_bypass_for_role,
    rls_enabled,
    sync_rls_from_request_context,
)
from app.services.brand_scope_service import (
    assert_marketplace_ibix_brand,
    assert_user_tenant_matches_request_brand,
)
from app.services.brand_service import BrandContext


def _brand(slug: str, brand_id: int, is_origem: bool) -> BrandContext:
    return BrandContext(
        id=brand_id,
        slug=slug,
        nome_exibicao=slug,
        nome_curto=slug,
        logo_url="/static/img/ibix/cab.png",
        logo_footer_url="/static/img/ibix/cab.png",
        favicon_url="/static/img/arte-pdv.png",
        telefone="",
        whatsapp="",
        email_remetente="",
        cor_primaria="#0066cc",
        cor_secundaria="#004499",
        seo_base_url=f"https://www.{slug}.com.br",
        is_origem=is_origem,
    )


def test_rls_enabled_default_off(monkeypatch):
    monkeypatch.delenv("RLS_ENABLED", raising=False)
    assert rls_enabled() is False
    monkeypatch.setenv("RLS_ENABLED", "true")
    assert rls_enabled() is True


def test_superadmin_bypass_role():
    assert resolve_rls_bypass_for_role("Superadministrador") is True
    assert resolve_rls_bypass_for_role("Cliente Administrador") is False
    assert resolve_rls_bypass_for_role(None) is False


def test_rls_tenant_policy_sql_shape():
    sql = RLS_TENANT_POLICY.format(table="usuarios")
    assert "rls_usuarios_tenant" in sql
    assert "app.bypass_rls" in sql
    assert "app.current_tenant" in sql


@patch("app.core.rls.rls_enabled", return_value=True)
def test_apply_rls_session_locals_executes_set_local(_mock_rls):
    db = MagicMock()
    apply_rls_session_locals(db, tenant_id=10, brand_id=2, bypass_rls=False)
    assert db.execute.call_count == 3
    calls = [str(c.args[0]) for c in db.execute.call_args_list]
    assert any("app.bypass_rls" in c for c in calls)
    assert any("app.current_tenant" in c for c in calls)
    assert any("app.current_brand" in c for c in calls)


@patch("app.core.rls.rls_enabled", return_value=True)
def test_sync_rls_from_request_context(_mock_rls):
    from app.core.request_context import clear_request_context, set_request_context

    clear_request_context()
    set_request_context(tenant_id=99, brand_id=1, bypass_rls=False)
    db = MagicMock()
    db.info = {}
    sync_rls_from_request_context(db)
    assert db.execute.call_count >= 3
    assert db.info["pdv_rls"]["tenant_id"] == 99


def test_cross_brand_tenant_mismatch_403():
    db = MagicMock()
    tenant = MagicMock()
    tenant.brand_id = 1
    tenant.id = 10
    db.query.return_value.filter.return_value.first.return_value = tenant

    user = MagicMock()
    user.tenant_id = 10

    request = MagicMock()
    request.state.brand = _brand("solumatica", brand_id=2, is_origem=False)

    with pytest.raises(HTTPException) as exc:
        assert_user_tenant_matches_request_brand(db, user, request)
    assert exc.value.status_code == 403


def test_marketplace_module_blocked_on_solumatica():
    request = MagicMock()
    request.state.brand = _brand("solumatica", brand_id=2, is_origem=False)
    with pytest.raises(HTTPException) as exc:
        assert_marketplace_ibix_brand(request)
    assert exc.value.status_code == 403


def test_marketplace_module_allowed_on_ibix():
    request = MagicMock()
    request.state.brand = _brand("ibix", brand_id=1, is_origem=True)
    assert_marketplace_ibix_brand(request)


def test_same_brand_tenant_allowed():
    db = MagicMock()
    tenant = MagicMock()
    tenant.brand_id = 2
    tenant.id = 10
    db.query.return_value.filter.return_value.first.return_value = tenant

    user = MagicMock()
    user.tenant_id = 10

    request = MagicMock()
    request.state.brand = _brand("solumatica", brand_id=2, is_origem=False)
    assert_user_tenant_matches_request_brand(db, user, request)
