"""Integração — listar_usuarios respeita marca do Host (DB real)."""
import pytest
from unittest.mock import MagicMock

from app.api.v1.usuarios import listar_usuarios
from app.database.connection import open_db_session
from app.models.usuario import Usuario
from app.services.brand_service import BrandContext, resolve_brand_by_host
from sqlalchemy.orm import joinedload


def _request_for_host(host: str):
    db = open_db_session(bypass_rls=True)
    brand = resolve_brand_by_host(db, host)
    db.close()
    request = MagicMock()
    request.state.brand = brand
    request.headers = {"host": host}
    request.client = MagicMock(host="127.0.0.1")
    return request


@pytest.mark.integration
def test_listar_usuarios_solumatica_superadmin_filtra_por_marca():
    db = open_db_session(bypass_rls=True)
    try:
        current = (
            db.query(Usuario)
            .options(joinedload(Usuario.role))
            .join(Usuario.role)
            .filter_by(nome="Superadministrador")
            .first()
        )
        if not current:
            pytest.skip("Sem superadmin no banco")

        request = _request_for_host("www.solumatica.com.br")
        result = listar_usuarios(
            request=request,
            skip=0,
            limit=500,
            ativo=None,
            nome=None,
            role_id=None,
            db=db,
            current_user=current,
        )
        assert result["total"] == 0
        assert result["usuarios"] == []
        assert result["brand_scope"]["scope_locked"] is True

        request_ibix = _request_for_host("www.ibix.com.br")
        result_ibix = listar_usuarios(
            request=request_ibix,
            skip=0,
            limit=500,
            ativo=None,
            nome=None,
            role_id=None,
            db=db,
            current_user=current,
        )
        assert result_ibix["total"] > 0
    finally:
        db.close()
