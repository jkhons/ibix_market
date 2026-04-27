# PDV Ibix - API Busca (autocomplete + populares) para consumidor mobile
"""Endpoints públicos de busca."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...database.connection import get_db
from ...schemas.mobile import AutocompleteResponse, TermoPopularResponse
from ...services.busca_service import autocomplete, registrar_termo, termos_populares

router = APIRouter(prefix="/loja/busca", tags=["Loja – Busca"])


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def busca_autocomplete(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    termos = autocomplete(db, q, limit=limit)
    if len(q) >= 3:
        registrar_termo(db, q)
    return {"termos": termos}


@router.get("/populares", response_model=list[TermoPopularResponse])
async def busca_populares(
    limit: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
):
    items = termos_populares(db, limit=limit)
    response = JSONResponse(content=items)
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response
