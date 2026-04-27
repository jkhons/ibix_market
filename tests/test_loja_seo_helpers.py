"""Testes das helpers de URL pública / cache-bust OG (Plano 01 vitrine)."""
import datetime as dt

import pytest


@pytest.fixture(scope="module")
def main_mod():
    import main as m

    return m


def test_absolute_public_https_none_without_base(main_mod):
    assert main_mod._absolute_public_https_url("", "/static/x.png") is None
    assert main_mod._absolute_public_https_url("   ", "/static/x.png") is None


def test_absolute_public_https_preserves_absolute(main_mod):
    assert main_mod._absolute_public_https_url("https://ignored.com", "https://cdn.example/z.png") == "https://cdn.example/z.png"


def test_absolute_public_https_joins_path(main_mod):
    assert main_mod._absolute_public_https_url("https://a.com", "/b/c.png") == "https://a.com/b/c.png"
    assert main_mod._absolute_public_https_url("https://a.com/", "b/c.png") == "https://a.com/b/c.png"


def test_og_image_cache_bust_appends_lastmod(main_mod):
    upd = dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc)
    out = main_mod._og_image_url_with_cache_bust("https://x.com/i.jpg", upd)
    assert out.startswith("https://x.com/i.jpg?lastmod=")
    out2 = main_mod._og_image_url_with_cache_bust("https://x.com/i.jpg?foo=1", upd)
    assert "&lastmod=" in out2


def test_og_image_cache_bust_no_date(main_mod):
    assert main_mod._og_image_url_with_cache_bust("https://x.com/i.jpg", None) == "https://x.com/i.jpg"
