# PDV Ibix — Gating de módulos por marca (Fase 2 multi-brand)
"""Resolução: brand_modules(brand). Entitlements por tenant entram na Fase 3 (brand_id)."""
from __future__ import annotations

from typing import AbstractSet, FrozenSet, Optional, Set

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.slug_utils import RESERVED_ROOT_SLUGS, SLUG_REGEX
from app.database.connection import get_db
from app.core.marketplace_rls import ensure_marketplace_loja_rls
from app.services.brand_service import brand_context_from_request

MODULE_CORE = "core"
MODULE_MARKETPLACE = "marketplace"
MODULE_CERTIFICADOS = "certificados"
MODULE_CALIBRATION = "calibracao"

MARKETPLACE_PUBLIC_EXACT_PATHS = frozenset({"/", "/index.html"})

MARKETPLACE_PUBLIC_PREFIXES = (
    "/loja",
    "/categoria/",
    "/lojas-parceiras",
    "/como-funciona-vitrine",
    "/politica-privacidade-marketplace",
    "/merchant-feed",
    "/negocio/marketplace",
    "/admin/marketing-vitrine",
    "/admin/marketing-ibix-lancamento",
    "/admin/marketplace-seo-lojas",
    "/admin/lojas_produtos",
)

MARKETPLACE_API_PREFIXES = (
    "/api/v1/loja",
    "/api/v1/marketing-vitrine",
    "/api/v1/marketing/ibix-lancamento",
    "/api/v1/marketplace",
    "/ws/loja",
)


def get_request_brand_module_slugs(request: Request) -> FrozenSet[str]:
    slugs = getattr(request.state, "brand_module_slugs", None)
    if slugs is None:
        return frozenset()
    return slugs if isinstance(slugs, frozenset) else frozenset(slugs)


def request_has_brand_module(request: Request, module_slug: str) -> bool:
    return module_slug in get_request_brand_module_slugs(request)


def path_requires_marketplace_module(path: str) -> bool:
    """True se a rota é da vitrine/marketplace pública ou API consumidor."""
    if not path:
        return False
    if path in MARKETPLACE_PUBLIC_EXACT_PATHS:
        return True
    if any(path.startswith(p) for p in MARKETPLACE_PUBLIC_PREFIXES):
        return True
    if any(path.startswith(p) for p in MARKETPLACE_API_PREFIXES):
        return True
    if path.startswith("/sitemap") and path != "/sitemap.xml":
        # sitemap de produtos/categorias/lojas marketplace
        return True
    # Vitrine pública /{slug-loja} na raiz
    if path.count("/") == 1 and path.startswith("/"):
        seg = path[1:].strip("/")
        if seg and seg not in RESERVED_ROOT_SLUGS and SLUG_REGEX.match(seg):
            return True
    return False


def load_brand_module_slugs(db: Session, brand_id: int) -> FrozenSet[str]:
    from app.core.redis_cache import get_brand_module_slugs_cached
    from app.services.brand_module_service import fetch_brand_module_slugs_from_db

    return get_brand_module_slugs_cached(
        brand_id,
        lambda: fetch_brand_module_slugs_from_db(db, brand_id),
    )


def require_brand_module(module_slug: str):
    """Dependency FastAPI: 403 se a marca atual não oferece o módulo."""

    async def _dep(request: Request, db: Session = Depends(get_db)):
        brand = brand_context_from_request(request)
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Marca não resolvida.",
            )
        if not hasattr(request.state, "brand_module_slugs"):
            request.state.brand_module_slugs = load_brand_module_slugs(db, brand.id)
        if not request_has_brand_module(request, module_slug):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Módulo '{module_slug}' indisponível nesta marca.",
            )

    return _dep


def marketplace_brand_available(request: Request) -> bool:
    return request_has_brand_module(request, MODULE_MARKETPLACE)


MARKETPLACE_ROUTER_DEPENDENCIES = [
    Depends(require_brand_module(MODULE_MARKETPLACE)),
    Depends(ensure_marketplace_loja_rls),
]
