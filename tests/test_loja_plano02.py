"""Plano 02 vitrine: redirect UTM + cookie, merge de atribuição no checkout."""
import pytest
from starlette.requests import Request
from starlette.testclient import TestClient

from app.api.v1.loja import _merge_checkout_single_attribution, _merge_checkout_unificado_attribution
from app.schemas.marketplace import (
    CheckoutItem,
    CheckoutItemUnificado,
    PedidoCheckoutCreate,
    PedidoCheckoutUnificadoCreate,
)


def _scope(path: str, query: bytes, cookie_header: bytes | None = None):
    h = []
    if cookie_header:
        h.append([b"cookie", cookie_header])
    return {
        "type": "http",
        "asgi": {"spec_version": "2.1", "version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query,
        "headers": h,
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
    }


@pytest.fixture(scope="module")
def main_client():
    import main as m

    return TestClient(m.app, raise_server_exceptions=False)


def test_loja_produto_utm_compartilhamento_redirect_strip_and_cookie(main_client):
    r = main_client.get(
        "/loja/produto/p-99?utm_source=compartilhamento&utm_medium=cliente&utm_campaign=vitrine_social&foo=bar",
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert r.headers.get("location") == "/loja/produto/p-99?foo=bar"
    set_cookie = r.headers.get("set-cookie") or ""
    assert "ibix_vitrine_share=1" in set_cookie
    assert "HttpOnly" in set_cookie


def test_merge_checkout_single_fills_from_cookie():
    req = Request(_scope("/x", b"", b"ibix_vitrine_share=1"))
    body = PedidoCheckoutCreate(
        loja_id=1,
        itens=[CheckoutItem(anuncio_id=1, quantidade=1)],
        comprador_nome="Nome",
        comprador_email="a@b.co",
        aceite_politica_privacidade=True,
    )
    out = _merge_checkout_single_attribution(req, body)
    assert out.utm_source == "compartilhamento"
    assert out.utm_medium == "cliente"
    assert out.utm_campaign == "vitrine_social"
    assert out.canal_origem == "share_cliente"


def test_merge_checkout_single_skips_when_utm_already_set():
    req = Request(_scope("/x", b"", b"ibix_vitrine_share=1"))
    body = PedidoCheckoutCreate(
        loja_id=1,
        itens=[CheckoutItem(anuncio_id=1, quantidade=1)],
        comprador_nome="Nome",
        comprador_email="a@b.co",
        aceite_politica_privacidade=True,
        utm_source="email",
    )
    out = _merge_checkout_single_attribution(req, body)
    assert out.utm_source == "email"
    assert out.canal_origem is None


def test_merge_checkout_single_no_cookie_no_change():
    req = Request(_scope("/x", b"", None))
    body = PedidoCheckoutCreate(
        loja_id=1,
        itens=[CheckoutItem(anuncio_id=1, quantidade=1)],
        comprador_nome="Nome",
        comprador_email="a@b.co",
        aceite_politica_privacidade=True,
    )
    out = _merge_checkout_single_attribution(req, body)
    assert out.utm_source is None
    assert out.canal_origem is None


def test_merge_checkout_unificado_fills_from_cookie():
    req = Request(_scope("/x", b"", b"ibix_vitrine_share=1"))
    body = PedidoCheckoutUnificadoCreate(
        itens=[CheckoutItemUnificado(anuncio_id=1, quantidade=1, loja_id=1)],
        comprador_nome="Nome",
        comprador_email="a@b.co",
        aceite_politica_privacidade=True,
    )
    out = _merge_checkout_unificado_attribution(req, body)
    assert out.utm_source == "compartilhamento"
    assert out.utm_campaign == "vitrine_social"
    assert out.canal_origem == "share_cliente"
