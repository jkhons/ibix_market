"""Testes de integração — middleware de gating marketplace por marca (Fase 2)."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.services.brand_service import BrandContext

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

SOLUMATICA_BRAND = BrandContext(
    id=2,
    slug="solumatica",
    nome_exibicao="Solumática",
    nome_curto="Solumática",
    logo_url="/static/img/solumatica/cab.png",
    logo_footer_url="/static/img/solumatica/cab.png",
    favicon_url="/static/img/arte-pdv.png",
    telefone="",
    whatsapp="",
    email_remetente="",
    cor_primaria="#0066cc",
    cor_secundaria="#004499",
    seo_base_url="https://www.solumatica.com.br",
    is_origem=False,
)

IBIX_MODULES = frozenset({"core", "marketplace"})
SOLUMATICA_MODULES = frozenset({"core"})


def _brand_side_effect(db, host):
    if "solumatica" in (host or ""):
        return SOLUMATICA_BRAND
    return IBIX_BRAND


def _modules_side_effect(db, brand_id):
    if brand_id == SOLUMATICA_BRAND.id:
        return SOLUMATICA_MODULES
    return IBIX_MODULES


@pytest.fixture
def brand_resolution_mocks():
    with (
        patch(
            "app.services.brand_service.resolve_brand_by_host",
            side_effect=_brand_side_effect,
        ) as mock_brand,
        patch(
            "app.core.brand_module_gating.load_brand_module_slugs",
            side_effect=_modules_side_effect,
        ) as mock_modules,
    ):
        yield mock_brand, mock_modules


@pytest.fixture
def client(brand_resolution_mocks):
    import sys

    # Garante que o patch precede o import de main (middleware importa brand_service por request).
    sys.modules.pop("main", None)
    from main import app

    return TestClient(app, raise_server_exceptions=False)


def test_marketplace_brand_available_por_modulos():
    from unittest.mock import MagicMock

    from app.core.brand_module_gating import marketplace_brand_available

    req_ibix = MagicMock()
    req_ibix.state.brand_module_slugs = IBIX_MODULES
    req_solumatica = MagicMock()
    req_solumatica.state.brand_module_slugs = SOLUMATICA_MODULES

    assert marketplace_brand_available(req_ibix) is True
    assert marketplace_brand_available(req_solumatica) is False


def test_ibix_permite_api_loja(client, brand_resolution_mocks):
    """Com mocks de marca, Ibix não recebe 403 de marketplace na API loja."""
    mock_brand, mock_modules = brand_resolution_mocks
    response = client.get(
        "/api/v1/loja/categorias",
        headers={"Host": "www.ibix.com.br"},
    )
    if not mock_brand.called:
        pytest.skip("Middleware de marca não invocou mock (main já carregado no processo)")
    assert response.status_code != 403 or "indisponível nesta marca" not in response.text


def test_solumatica_bloqueia_api_loja(client, brand_resolution_mocks):
    response = client.get(
        "/api/v1/loja/categorias",
        headers={"Host": "www.solumatica.com.br"},
    )
    assert response.status_code == 403
    assert "marketplace" in response.json().get("detail", "").lower()


def test_solumatica_bloqueia_vitrine_html(client, brand_resolution_mocks):
    response = client.get(
        "/loja",
        headers={"Host": "www.solumatica.com.br"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers.get("location") == "/login"


def test_solumatica_exibe_landing_na_raiz(client, brand_resolution_mocks):
    response = client.get(
        "/",
        headers={"Host": "www.solumatica.com.br"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Sistema de Vendas e Gestão" in response.text
    assert "Solumática" in response.text
    assert "fale-conosco-form" in response.text


def test_solumatica_nao_bloqueia_dashboard_via_middleware(client, brand_resolution_mocks):
    """Dashboard é rota core; middleware não deve devolver 403 JSON de marketplace."""
    response = client.get(
        "/dashboard",
        headers={"Host": "www.solumatica.com.br"},
        follow_redirects=False,
    )
    assert response.status_code != 403 or "application/json" not in response.headers.get(
        "content-type", ""
    )


def test_solumatica_bloqueia_marketing_vitrine_api(client, brand_resolution_mocks):
    response = client.get(
        "/api/v1/marketing-vitrine/config",
        headers={"Host": "www.solumatica.com.br"},
    )
    assert response.status_code == 403


def test_solumatica_bloqueia_marketing_ibix_lancamento_api(client, brand_resolution_mocks):
    response = client.get(
        "/api/v1/marketing/ibix-lancamento/campanha",
        headers={"Host": "www.solumatica.com.br"},
    )
    assert response.status_code == 403


def test_ibix_permite_home_vitrine(client, brand_resolution_mocks):
    response = client.get(
        "/",
        headers={"Host": "www.ibix.com.br"},
        follow_redirects=False,
    )
    assert response.status_code != 403, "Ibix não deveria receber 403 na home da vitrine"
