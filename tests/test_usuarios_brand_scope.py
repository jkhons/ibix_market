"""Testes — listagem de usuários com escopo de marca."""
from unittest.mock import MagicMock, patch

from app.api.v1.usuarios import listar_usuarios
from app.services.brand_service import BrandContext


def _solumatica_request():
    request = MagicMock()
    request.state.brand = BrandContext(
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
        seo_base_url="",
        is_origem=False,
    )
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"host": "www.solumatica.com.br"}
    return request


def test_listar_usuarios_superadmin_sem_tenants_marca_retorna_vazio():
    db = MagicMock()
    current_user = MagicMock()
    current_user.role = MagicMock(nome="Superadministrador")

    with (
        patch("app.api.v1.usuarios.resolve_admin_brand_scope", return_value=2),
        patch("app.api.v1.usuarios.tenant_ids_for_admin_brand", return_value=[]),
        patch("app.api.v1.usuarios.brand_scope_meta", return_value={"brand_id": 2, "scope_locked": True}),
    ):
        result = listar_usuarios(
            request=_solumatica_request(),
            skip=0,
            limit=100,
            ativo=None,
            nome=None,
            role_id=None,
            db=db,
            current_user=current_user,
        )

    assert result["total"] == 0
    assert result["usuarios"] == []
    assert result["brand_scope"]["brand_id"] == 2
    db.query.assert_not_called()


def test_listar_usuarios_superadmin_marca_derivada_usa_escopo():
    db = MagicMock()
    current_user = MagicMock()
    current_user.role = MagicMock(nome="Superadministrador")

    query_chain = MagicMock()
    db.query.return_value = query_chain
    query_chain.filter.return_value = query_chain
    scoped_chain = MagicMock()
    scoped_chain.options.return_value = scoped_chain
    scoped_chain.filter.return_value = scoped_chain
    scoped_chain.count.return_value = 0
    scoped_chain.offset.return_value.limit.return_value.all.return_value = []

    with (
        patch("app.api.v1.usuarios.resolve_admin_brand_scope", return_value=2),
        patch("app.api.v1.usuarios.tenant_ids_for_admin_brand", return_value=[99]),
        patch("app.api.v1.usuarios._scoped_usuarios_query", return_value=(scoped_chain, False)),
        patch("app.api.v1.usuarios.brand_scope_meta", return_value={"brand_id": 2}),
        patch("app.api.v1.usuarios.user_can_view_pii", return_value=True),
    ):
        listar_usuarios(
            request=_solumatica_request(),
            skip=0,
            limit=100,
            ativo=None,
            nome=None,
            role_id=None,
            db=db,
            current_user=current_user,
        )

    scoped_chain.options.assert_called_once()
