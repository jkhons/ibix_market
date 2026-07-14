"""Testes — get_template_context expõe brand_scope."""
from unittest.mock import MagicMock, patch

from main import get_template_context


def test_get_template_context_brand_scope_derivada():
    request = MagicMock()
    request.state.brand_module_slugs = frozenset({"core"})
    request.state.csp_nonce = "n"
    request.state.user_id = None
    request.cookies = {}

    brand_dict = {
        "id": 2,
        "slug": "solumatica",
        "nome_exibicao": "Solumática",
        "nome": "Solumática",
        "is_origem": False,
    }
    db = MagicMock()

    with patch("main._brand_template_dict", return_value=brand_dict):
        ctx = get_template_context(request, db)

    assert "brand_scope" in ctx
    assert ctx["brand_scope"]["scope_locked"] is True
    assert ctx["brand_scope"]["scope_label"] == "Dados: Solumática"


def test_get_template_context_brand_scope_origem():
    request = MagicMock()
    request.state.brand_module_slugs = frozenset({"core", "marketplace"})
    request.state.csp_nonce = "n"
    request.state.user_id = None
    request.cookies = {}

    brand_dict = {
        "id": 1,
        "slug": "ibix",
        "nome_exibicao": "PDV Ibix",
        "nome": "Ibix",
        "is_origem": True,
    }
    db = MagicMock()

    with patch("main._brand_template_dict", return_value=brand_dict):
        ctx = get_template_context(request, db)

    assert ctx["brand_scope"]["scope_locked"] is False
    assert "Visão global" in ctx["brand_scope"]["scope_label"]
