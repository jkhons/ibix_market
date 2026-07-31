# PDV Ibix - API Favoritos do consumidor mobile
"""CRUD de favoritos (wishlist) — requer consumidor autenticado."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.error_codes import ANUNCIO_NAO_ENCONTRADO, FAVORITO_NAO_ENCONTRADO
from ...database.connection import get_db
from ...schemas.mobile import FavoritosListResponse
from ...services.favorito_service import (
    adicionar_favorito,
    listar_favoritos,
    remover_favorito,
)
from .loja import get_current_consumidor

from ...core.brand_module_gating import MARKETPLACE_ROUTER_DEPENDENCIES

router = APIRouter(
    prefix="/loja/favoritos",
    tags=["Loja – Favoritos"],
    dependencies=MARKETPLACE_ROUTER_DEPENDENCIES,
)


@router.get("", response_model=FavoritosListResponse)
async def listar_meus_favoritos(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    items, total = listar_favoritos(db, consumidor.id, offset=offset, limit=limit)
    return {"items": items, "total": total}


@router.post("/{anuncio_id}", status_code=status.HTTP_201_CREATED)
async def adicionar_favorito_endpoint(
    anuncio_id: int,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    try:
        fav = adicionar_favorito(db, consumidor.id, anuncio_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Anúncio não encontrado", "code": ANUNCIO_NAO_ENCONTRADO},
        )
    return {"id": fav.id, "anuncio_id": fav.anuncio_id}


@router.delete("/{anuncio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_favorito_endpoint(
    anuncio_id: int,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    removed = remover_favorito(db, consumidor.id, anuncio_id)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Favorito não encontrado", "code": FAVORITO_NAO_ENCONTRADO},
        )
