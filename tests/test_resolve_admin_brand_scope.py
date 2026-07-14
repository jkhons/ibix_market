"""Testes — resolve_admin_brand_scope e metadados de escopo admin."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.brand_scope_service import (
    brand_scope_meta,
    resolve_admin_brand_scope,
)
from app.services.brand_service import BrandContext


def _brand(slug: str, is_origem: bool, brand_id: int) -> BrandContext:
    return BrandContext(
        id=brand_id,
        slug=slug,
        nome_exibicao=f"PDV {slug.title()}",
        nome_curto=slug.title(),
        logo_url="/static/img/ibix/cab.png",
        logo_footer_url="/static/img/ibix/cab.png",
        favicon_url="/static/img/arte-pdv.png",
        telefone="",
        whatsapp="",
        email_remetente="",
        cor_primaria="#0066cc",
        cor_secundaria="#004499",
        seo_base_url=f"https://www.{slug}.com.br",
        is_origem=is_origem,
    )


def test_resolve_admin_brand_scope_marca_derivada_forca_host():
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.state.brand = _brand("solumatica", is_origem=False, brand_id=2)
    db = MagicMock()
    with patch("app.services.brand_scope_service.brand_context_from_request", return_value=request.state.brand):
        assert resolve_admin_brand_scope(request, db) == 2
        assert resolve_admin_brand_scope(request, db, brand_id=2) == 2


def test_resolve_admin_brand_scope_marca_derivada_rejeita_cross_brand():
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.state.brand = _brand("solumatica", is_origem=False, brand_id=2)
    db = MagicMock()
    with patch("app.services.brand_scope_service.brand_context_from_request", return_value=request.state.brand):
        with pytest.raises(HTTPException) as exc:
            resolve_admin_brand_scope(request, db, brand_id=1)
    assert exc.value.status_code == 403


def test_resolve_admin_brand_scope_origem_permite_none():
    request = MagicMock()
    request.state.brand = _brand("ibix", is_origem=True, brand_id=1)
    db = MagicMock()
    with patch("app.services.brand_scope_service.brand_context_from_request", return_value=request.state.brand):
        assert resolve_admin_brand_scope(request, db) is None


def test_resolve_admin_brand_scope_origem_filtra_por_query():
    request = MagicMock()
    request.state.brand = _brand("ibix", is_origem=True, brand_id=1)
    db = MagicMock()
    brand_row = MagicMock(id=2, ativo=True)
    db.query.return_value.filter.return_value.first.return_value = brand_row
    with patch("app.services.brand_scope_service.brand_context_from_request", return_value=request.state.brand):
        assert resolve_admin_brand_scope(request, db, brand_id=2) == 2


def test_brand_scope_meta_derivada_locked():
    request = MagicMock()
    request.state.brand = _brand("solumatica", is_origem=False, brand_id=2)
    db = MagicMock()
    row = MagicMock(nome_exibicao="Solumática", slug="solumatica")
    db.query.return_value.filter.return_value.first.return_value = row
    with patch("app.services.brand_scope_service.brand_context_from_request", return_value=request.state.brand):
        meta = brand_scope_meta(request, db, 2)
    assert meta["brand_id"] == 2
    assert meta["scope_locked"] is True
    assert "Solumática" in meta["scope_label"]


def test_brand_scope_meta_origem_global():
    request = MagicMock()
    request.state.brand = _brand("ibix", is_origem=True, brand_id=1)
    db = MagicMock()
    with patch("app.services.brand_scope_service.brand_context_from_request", return_value=request.state.brand):
        meta = brand_scope_meta(request, db, None)
    assert meta["brand_id"] is None
    assert meta["scope_locked"] is False
    assert "Visão global" in meta["scope_label"]
