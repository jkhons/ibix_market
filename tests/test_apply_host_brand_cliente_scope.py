"""Testes — apply_host_brand_cliente_scope (dashboard / negócios)."""
from unittest.mock import MagicMock, patch

from app.core.scope import ClienteScope
from app.services.brand_scope_service import apply_host_brand_cliente_scope
from app.services.brand_service import BrandContext


def _solumatica_brand() -> BrandContext:
    return BrandContext(
        id=2,
        slug="solumatica",
        nome_exibicao="Solumática",
        nome_curto="Solumática",
        logo_url="",
        logo_footer_url="",
        favicon_url="",
        telefone="",
        whatsapp="",
        email_remetente="",
        cor_primaria="",
        cor_secundaria="",
        seo_base_url="https://www.solumatica.com.br",
        is_origem=False,
    )


def test_superadmin_em_solumatica_filtra_por_marca():
    request = MagicMock()
    request.headers = {"host": "www.solumatica.com.br"}
    db = MagicMock()
    scope = ClienteScope(allowed_ids=[], is_superadmin=True, see_all=False)

    with (
        patch(
            "app.services.brand_scope_service._brand_from_request_resolved",
            return_value=_solumatica_brand(),
        ),
        patch("app.core.scope.get_cliente_ids_for_brand", return_value=[10, 20]),
    ):
        out = apply_host_brand_cliente_scope(request, db, scope)

    assert out.must_filter_by_cliente() is True
    assert out.allowed_ids == [10, 20]


def test_administrador_em_solumatica_intersecta_escopo():
    request = MagicMock()
    request.headers = {"host": "www.solumatica.com.br"}
    db = MagicMock()
    scope = ClienteScope(allowed_ids=[10, 99], is_superadmin=False, see_all=False)

    with (
        patch(
            "app.services.brand_scope_service._brand_from_request_resolved",
            return_value=_solumatica_brand(),
        ),
        patch("app.core.scope.get_cliente_ids_for_brand", return_value=[10, 20]),
    ):
        out = apply_host_brand_cliente_scope(request, db, scope)

    assert out.allowed_ids == [10]


def test_ibix_origem_mantem_superadmin_global():
    request = MagicMock()
    request.headers = {"host": "www.ibix.com.br"}
    db = MagicMock()
    ibix = BrandContext(
        id=1,
        slug="ibix",
        nome_exibicao="Ibix",
        nome_curto="Ibix",
        logo_url="",
        logo_footer_url="",
        favicon_url="",
        telefone="",
        whatsapp="",
        email_remetente="",
        cor_primaria="",
        cor_secundaria="",
        seo_base_url="https://www.ibix.com.br",
        is_origem=True,
    )
    scope = ClienteScope(allowed_ids=[], is_superadmin=True, see_all=False)

    with patch(
        "app.services.brand_scope_service._brand_from_request_resolved",
        return_value=ibix,
    ):
        out = apply_host_brand_cliente_scope(request, db, scope)

    assert out.is_superadmin is True
    assert out.must_filter_by_cliente() is False
