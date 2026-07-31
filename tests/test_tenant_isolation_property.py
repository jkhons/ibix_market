# Property-style tests — isolamento cross-brand (Fase 9 CI)
"""Variações de slug/host para garantir 403 marketplace fora da Ibix."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.brand_module_gating import path_requires_marketplace_module
from app.services.brand_scope_service import assert_marketplace_ibix_brand
from app.services.brand_service import BrandContext


def _brand(slug: str, brand_id: int, is_origem: bool) -> BrandContext:
    return BrandContext(
        id=brand_id,
        slug=slug,
        nome_exibicao=slug,
        nome_curto=slug,
        logo_url="/static/x.png",
        logo_footer_url="/static/x.png",
        favicon_url="/static/x.png",
        telefone="",
        whatsapp="",
        email_remetente="",
        cor_primaria="#000",
        cor_secundaria="#111",
        seo_base_url=f"https://www.{slug}.com.br",
        is_origem=is_origem,
    )


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/loja", True),
        ("/api/v1/loja/categorias", True),
        ("/login", False),
        ("/dashboard", False),
        ("/negocio/estoque", False),
    ],
)
def test_marketplace_path_detection(path, expected):
    assert path_requires_marketplace_module(path) is expected


@pytest.mark.parametrize("slug", ["solumatica", "certipeso", "marca-x"])
def test_non_ibix_marketplace_blocked(slug):
    request = MagicMockRequest(_brand(slug, brand_id=2, is_origem=False))
    with pytest.raises(HTTPException) as exc:
        assert_marketplace_ibix_brand(request)
    assert exc.value.status_code == 403


class MagicMockRequest:
    def __init__(self, brand: BrandContext):
        self.state = MagicMockState(brand)


class MagicMockState:
    def __init__(self, brand: BrandContext):
        self.brand = brand
