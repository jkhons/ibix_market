"""Testes — hardening Fase 5 (CORS, CSP, rate limit por marca, métricas)."""
from unittest.mock import MagicMock

import pytest

from app.core.hardening import (
    build_csp_header,
    is_metrics_client_allowed,
    merge_cors_allowlist,
    origins_from_brand_rows,
    parse_cors_origins_env,
    public_origin_from_request,
    rate_limit_brand_slug,
    resolve_cors_allowlist,
)
from app.core.rate_limiter import get_brand_scoped_rate_key
from app.services.brand_service import BrandContext


def _brand(slug: str, seo: str) -> BrandContext:
    return BrandContext(
        id=1 if slug == "ibix" else 2,
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
        seo_base_url=seo,
        is_origem=slug == "ibix",
    )


def test_parse_cors_origins_env():
    assert parse_cors_origins_env("https://a.com, https://b.com") == [
        "https://a.com",
        "https://b.com",
    ]


def test_origins_from_brand_rows():
    brand = MagicMock(ativo=True, seo_base_url="https://www.solumatica.com.br")
    domain = MagicMock(ativo=True, dominio="auto.solumatica.com.br")
    out = origins_from_brand_rows([brand], [domain])
    assert "https://www.solumatica.com.br" in out
    assert "https://auto.solumatica.com.br" in out
    assert "https://solumatica.com.br" in out


def test_resolve_cors_production_merges_env_and_db():
    db = MagicMock()
    brand = MagicMock(ativo=True, seo_base_url="https://www.solumatica.com.br")
    domain = MagicMock(ativo=True, dominio="www.ibix.com.br")
    db.query.return_value.filter.return_value.all.side_effect = [[brand], [domain]]
    result = resolve_cors_allowlist(
        db=db,
        is_production=True,
    )
    assert "https://www.ibix.com.br" in result
    assert "https://www.solumatica.com.br" in result
    assert "*" not in result


def test_resolve_cors_production_rejects_wildcard(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="wildcard"):
        resolve_cors_allowlist(db=None, is_production=True)


def test_build_csp_includes_brand_host():
    csp_ibix = build_csp_header(_brand("ibix", "https://www.ibix.com.br"))
    csp_solum = build_csp_header(_brand("solumatica", "https://www.solumatica.com.br"))
    assert "https://www.ibix.com.br" in csp_ibix
    assert "https://www.solumatica.com.br" in csp_solum
    assert "https://*.ibix.com.br" in csp_ibix


def test_is_metrics_client_allowed_localhost_only():
    assert is_metrics_client_allowed("127.0.0.1") is True
    assert is_metrics_client_allowed("::1") is True
    assert is_metrics_client_allowed("10.0.0.1") is False


def test_is_metrics_client_allowed_remote_flag(monkeypatch):
    monkeypatch.setenv("METRICS_ALLOW_REMOTE", "true")
    assert is_metrics_client_allowed("203.0.113.1") is True


def test_rate_limit_brand_slug():
    request = MagicMock()
    request.state.brand = _brand("solumatica", "https://www.solumatica.com.br")
    assert rate_limit_brand_slug(request) == "solumatica"
    request.state.brand = None
    assert rate_limit_brand_slug(request) == "unknown"


def test_get_brand_scoped_rate_key():
    request = MagicMock()
    request.state.brand = _brand("ibix", "https://www.ibix.com.br")
    request.headers.get.return_value = None
    request.client.host = "192.0.2.1"
    assert get_brand_scoped_rate_key(request) == "ibix:192.0.2.1"


def test_public_origin_from_request_uses_brand_seo():
    request = MagicMock()
    request.state.brand = _brand("solumatica", "https://www.solumatica.com.br")
    request.headers.get.return_value = "www.solumatica.com.br"
    request.url.scheme = "http"
    assert public_origin_from_request(request) == "https://www.solumatica.com.br"


def test_merge_cors_allowlist_dedupes():
    merged = merge_cors_allowlist(
        ["https://www.ibix.com.br"],
        ["https://www.ibix.com.br", "https://www.solumatica.com.br"],
    )
    assert merged == ["https://www.ibix.com.br", "https://www.solumatica.com.br"]
