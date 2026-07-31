# PDV Ibix - API Notificações in-app do consumidor mobile
"""Listagem e marcação de notificações — requer consumidor autenticado."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...database.connection import get_db
from ...schemas.mobile import (
    NotificacaoMarcarLidaRequest,
    NotificacoesListResponse,
)
from ...services.notificacao_service import listar_notificacoes, marcar_lidas
from .loja import get_current_consumidor

from ...core.brand_module_gating import MARKETPLACE_ROUTER_DEPENDENCIES

router = APIRouter(
    prefix="/loja/notificacoes",
    tags=["Loja – Notificações"],
    dependencies=MARKETPLACE_ROUTER_DEPENDENCIES,
)


@router.get("", response_model=NotificacoesListResponse)
async def listar_minhas_notificacoes(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    items, total, nao_lidas = listar_notificacoes(db, consumidor.id, offset=offset, limit=limit)
    return {"items": items, "total": total, "nao_lidas": nao_lidas}


@router.patch("/lidas")
async def marcar_notificacoes_lidas(
    body: NotificacaoMarcarLidaRequest,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    count = marcar_lidas(db, consumidor.id, ids=body.ids)
    return {"marcadas": count}
