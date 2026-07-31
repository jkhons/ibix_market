# PDV Ibix — RLS para API marketplace consumidor (Ibix Market / vitrine /loja)
"""Catálogo cross-tenant e pedidos multi-loja: isolamento na camada app (JWT, comprador_id)."""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.request_context import update_request_context
from app.core.rls import sync_rls_from_request_context
from app.database.connection import get_db
from app.services.brand_service import brand_context_from_request


def apply_marketplace_loja_rls_context(db: Session, request: Request) -> None:
    """
    Rotas /api/v1/loja/* e /api/v1/marketing-vitrine/* (marca Ibix).

    Com RLS ativo, tenant_id único não cobre:
    - vitrine pública (vários tenants);
    - meus-pedidos (checkout multi-loja);
    - login por e-mail (consumidor platform-wide tenant_id NULL).

    bypass_rls=True aqui é deliberado; guards: gating marketplace, assert_marketplace_ibix_brand,
    JWT consumidor e filtros por comprador_id/endereço nas queries.
    """
    brand = brand_context_from_request(request)
    update_request_context(
        brand_id=brand.id if brand else None,
        bypass_rls=True,
    )
    sync_rls_from_request_context(db)


async def ensure_marketplace_loja_rls(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    apply_marketplace_loja_rls_context(db, request)


__all__ = [
    "apply_marketplace_loja_rls_context",
    "ensure_marketplace_loja_rls",
]
