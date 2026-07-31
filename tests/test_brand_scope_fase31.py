"""Testes — escopo de marca Fase 3.1 (tenant slug, cookies, consumidor Ibix)."""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.brand_cookie import apply_host_scoped_cookie
from app.services.brand_scope_service import (
    assert_marketplace_ibix_brand,
    assert_user_tenant_matches_request_brand,
)
from app.services.brand_service import BrandContext


def _brand(slug: str, is_origem: bool, brand_id: int) -> BrandContext:
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


def test_apply_host_scoped_cookie_sem_domain():
    response = MagicMock()
    apply_host_scoped_cookie(response, key="test_cookie", value="abc", max_age=60)
    kwargs = response.set_cookie.call_args.kwargs
    assert kwargs["key"] == "test_cookie"
    assert "domain" not in kwargs


def test_assert_marketplace_ibix_brand_rejeita_solumatica():
    request = MagicMock()
    request.state.brand = _brand("solumatica", is_origem=False, brand_id=2)
    with pytest.raises(HTTPException) as exc:
        assert_marketplace_ibix_brand(request)
    assert exc.value.status_code == 403


def test_assert_marketplace_ibix_brand_aceita_origem():
    request = MagicMock()
    request.state.brand = _brand("ibix", is_origem=True, brand_id=1)
    assert_marketplace_ibix_brand(request)


def test_assert_user_tenant_brand_mismatch():
    db = MagicMock()
    tenant = MagicMock()
    tenant.brand_id = 1
    tenant.id = 10
    db.query.return_value.filter.return_value.first.return_value = tenant

    user = MagicMock()
    user.tenant_id = 10

    request = MagicMock()
    request.state.brand = _brand("solumatica", is_origem=False, brand_id=2)

    with pytest.raises(HTTPException) as exc:
        assert_user_tenant_matches_request_brand(db, user, request)
    assert exc.value.status_code == 403
