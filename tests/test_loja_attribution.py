# PDV Ibix — atribuição vitrine (Fase 02)
from starlette.requests import Request

from app.core.loja_attribution import strip_utm_params_from_path_query, vitrine_share_cookie_present


def _req(path: str, query_string: bytes = b"") -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"spec_version": "2.1", "version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode(),
            "query_string": query_string,
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("test", 443),
        }
    )


def test_strip_utm_removes_known_params_keeps_others():
    r = _req("/loja/x/p/1", b"utm_source=compartilhamento&utm_medium=cliente&foo=bar&UTM_CAMPAIGN=x")
    assert strip_utm_params_from_path_query(r) == "/loja/x/p/1?foo=bar"


def test_strip_utm_empty_query_returns_path_only():
    r = _req("/p", b"")
    assert strip_utm_params_from_path_query(r) == "/p"


def test_vitrine_share_cookie_present():
    r = _req("/p")
    assert vitrine_share_cookie_present(r) is False
    r2 = Request(
        {
            "type": "http",
            "asgi": {"spec_version": "2.1", "version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/p",
            "raw_path": b"/p",
            "query_string": b"",
            "headers": [[b"cookie", b"ibix_vitrine_share=1"]],
            "client": ("127.0.0.1", 12345),
            "server": ("test", 443),
        }
    )
    assert vitrine_share_cookie_present(r2) is True
