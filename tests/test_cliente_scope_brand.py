"""Testes — ClienteScope com escopo de marca para Superadmin."""
from unittest.mock import MagicMock, patch

from app.core.middleware import get_cliente_scope_dep
from app.core.scope import ClienteScope
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


def test_superadmin_em_marca_derivada_filtra_clientes():
    request = MagicMock()
    request.state.brand = _solumatica_brand()
    db = MagicMock()
    user = MagicMock()
    user.id = 1
    user.role = MagicMock(nome="Superadministrador")

    with (
        patch("app.core.middleware.get_cliente_scope") as mock_scope,
        patch("app.core.scope.get_cliente_ids_for_brand", return_value=[10, 20]),
    ):
        mock_scope.return_value = ClienteScope(allowed_ids=[], is_superadmin=True, see_all=False)
        scope = get_cliente_scope_dep(request, user, db, None)

    assert scope.is_superadmin is False
    assert scope.must_filter_by_cliente() is True
    assert scope.allowed_ids == [10, 20]


def test_superadmin_em_origem_mantem_escopo_global():
    request = MagicMock()
    request.state.brand = BrandContext(
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
    db = MagicMock()
    user = MagicMock()
    user.id = 1
    user.role = MagicMock(nome="Superadministrador")

    with patch("app.core.middleware.get_cliente_scope") as mock_scope:
        mock_scope.return_value = ClienteScope(allowed_ids=[], is_superadmin=True, see_all=False)
        scope = get_cliente_scope_dep(request, user, db, None)

    assert scope.is_superadmin is True
    assert scope.must_filter_by_cliente() is False
