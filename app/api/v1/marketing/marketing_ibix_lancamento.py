# PDV Ibix — API Marketing Ibix Lançamento (Superadmin + brand marketplace)
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.brand_module_gating import MARKETPLACE_ROUTER_DEPENDENCIES
from app.core.middleware import require_superadmin
from app.database.connection import get_db
from app.models import Usuario
from app.schemas.marketing_ibix_lancamento import (
    MarketingCampanhaPatch,
    MarketingCampanhaResumo,
    MarketingPostOut,
    MarketingPostPatch,
)
from app.services import marketing_ibix_lancamento_service as svc

router = APIRouter(
    prefix="/marketing/ibix-lancamento",
    tags=["Marketing Ibix Lançamento"],
    dependencies=MARKETPLACE_ROUTER_DEPENDENCIES,
)


@router.get("/campanha", response_model=MarketingCampanhaResumo)
def get_campanha(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    _ = current_user
    return svc.build_campanha_resumo(db)


@router.patch("/campanha", response_model=MarketingCampanhaResumo)
def patch_campanha_endpoint(
    body: MarketingCampanhaPatch,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    _ = current_user
    svc.patch_campanha(db, body)
    return svc.build_campanha_resumo(db)


@router.get("/posts", response_model=List[MarketingPostOut])
def list_posts(
    bloco: Optional[str] = Query(None, pattern="^[ABCD]$"),
    status_copy: Optional[str] = Query(None),
    status_publicacao: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    _ = current_user
    rows = svc.listar_posts(
        db,
        bloco=bloco,
        status_copy=status_copy,
        status_publicacao=status_publicacao,
    )
    return [svc.post_to_out(r) for r in rows]


@router.get("/posts/{numero}", response_model=MarketingPostOut)
def get_post(
    numero: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    _ = current_user
    return svc.post_to_out(svc.get_post(db, numero))


@router.patch("/posts/{numero}", response_model=MarketingPostOut)
def patch_post(
    numero: int,
    body: MarketingPostPatch,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    row = svc.patch_post(db, numero, body, user_id=int(current_user.id))
    return svc.post_to_out(row)
