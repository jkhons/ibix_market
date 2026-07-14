"""Testes — endpoint leve /usuarios/representantes."""
from unittest.mock import MagicMock, patch

from app.api.v1.usuarios import listar_representantes
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


def test_representantes_marca_sem_tenants_retorna_vazio():
    db = MagicMock()
    current_user = MagicMock()
    current_user.role = MagicMock(nome="Superadministrador")

    with (
        patch("app.api.v1.usuarios.resolve_admin_brand_scope", return_value=2),
        patch("app.api.v1.usuarios.tenant_ids_for_admin_brand", return_value=[]),
        patch("app.api.v1.usuarios._admin_role_id", return_value=2),
    ):
        result = listar_representantes(request=_solumatica_request(), db=db, current_user=current_user)

    assert result == {"representantes": [], "total": 0}
    db.query.assert_not_called()
