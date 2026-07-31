"""Testes unitários — resolução de marca por Host (Fase 1 multi-brand)."""
from app.services.brand_service import normalize_host


def test_normalize_host_strips_port_and_lowercase():
    assert normalize_host("WWW.Ibix.com.br:443") == "www.ibix.com.br"
    assert normalize_host("  Solumatica.COM.br  ") == "solumatica.com.br"
    assert normalize_host(None) == ""
    assert normalize_host("") == ""
