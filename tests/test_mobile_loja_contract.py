"""Contrato API mobile Ibix Market — header X-Client: mobile (P-M4)."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.services.brand_service import BrandContext

MOBILE_HEADERS = {
    "Host": "www.ibix.com.br",
    "X-Client": "mobile",
    "X-Client-Version": "1.0.0",
}

IBIX_BRAND = BrandContext(
    id=1,
    slug="ibix",
    nome_exibicao="Ibix",
    nome_curto="Ibix",
    logo_url="/static/img/ibix/cab.png",
    logo_footer_url="/static/img/ibix/cab.png",
    favicon_url="/static/img/arte-pdv.png",
    telefone="",
    whatsapp="",
    email_remetente="",
    cor_primaria="#0066cc",
    cor_secundaria="#004499",
    seo_base_url="https://www.ibix.com.br",
    is_origem=True,
)

IBIX_MODULES = frozenset({"core", "marketplace"})


def _brand_side_effect(db, host):
    return IBIX_BRAND


def _modules_side_effect(db, brand_id):
    return IBIX_MODULES


@pytest.fixture
def mobile_client():
    with (
        patch(
            "app.services.brand_service.resolve_brand_by_host",
            side_effect=_brand_side_effect,
        ),
        patch(
            "app.core.brand_module_gating.load_brand_module_slugs",
            side_effect=_modules_side_effect,
        ),
    ):
        import sys

        sys.modules.pop("main", None)
        from main import app

        yield TestClient(app, raise_server_exceptions=False)


def test_mobile_categorias_200(mobile_client):
    r = mobile_client.get("/api/v1/loja/categorias", headers=MOBILE_HEADERS)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_mobile_anuncios_200(mobile_client):
    r = mobile_client.get("/api/v1/loja/anuncios", params={"limit": 5}, headers=MOBILE_HEADERS)
    assert r.status_code == 200


def test_mobile_vitrine_home_200(mobile_client):
    r = mobile_client.get("/api/v1/marketing-vitrine/vitrine-home", headers=MOBILE_HEADERS)
    assert r.status_code == 200


def test_mobile_app_version_not_403(mobile_client):
    r = mobile_client.get("/api/v1/loja/app-version", headers=MOBILE_HEADERS)
    assert r.status_code != 403
    assert "indisponível nesta marca" not in r.text.lower()


def test_mobile_login_requires_body(mobile_client):
    r = mobile_client.post("/api/v1/loja/login", json={}, headers=MOBILE_HEADERS)
    assert r.status_code in (401, 422)


def test_marketplace_rls_bypass_applied():
    from unittest.mock import MagicMock, patch

    from app.core.marketplace_rls import apply_marketplace_loja_rls_context
    from app.core.request_context import clear_request_context, get_request_context

    clear_request_context()
    db = MagicMock()
    request = MagicMock()
    request.state.brand = IBIX_BRAND

    with patch("app.core.rls.rls_enabled", return_value=True):
        apply_marketplace_loja_rls_context(db, request)

    ctx = get_request_context()
    assert ctx.get("bypass_rls") is True
    assert ctx.get("brand_id") == 1
    assert db.execute.called
    clear_request_context()
