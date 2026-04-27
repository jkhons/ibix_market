# PDV Ibix - Admin: preços PDV (Fase 2)
"""CRUD de preços de licença PDV. Apenas SuperAdmin."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.audit import audit_action
from ...core.middleware import require_superadmin
from ...core.scope import resolve_tenant_pagador
from ...database.connection import get_db
from ...models import Usuario
from ...models.preco_pdv import PrecoPdv
from ...schemas.preco_pdv import PrecoPdvCreate, PrecoPdvResponse, PrecoPdvUpdate

router = APIRouter(prefix="/admin/precos-pdv", tags=["Admin Preços PDV"])


def _get_preco_vigente(db: Session) -> PrecoPdv | None:
    return (
        db.query(PrecoPdv)
        .filter(PrecoPdv.ativo == True)
        .order_by(PrecoPdv.vigencia_inicio.desc())
        .first()
    )


@router.get("/", response_model=List[PrecoPdvResponse])
def listar_precos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    return db.query(PrecoPdv).order_by(PrecoPdv.vigencia_inicio.desc()).all()


@router.get("/vigente", response_model=PrecoPdvResponse)
def preco_vigente(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    preco = _get_preco_vigente(db)
    if not preco:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum preço vigente configurado")
    return preco


@router.post("/", response_model=PrecoPdvResponse, status_code=status.HTTP_201_CREATED)
def criar_preco(
    body: PrecoPdvCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    preco = PrecoPdv(
        valor_base_centavos=body.valor_base_centavos,
        valor_pdv_adicional_centavos=body.valor_pdv_adicional_centavos,
        vigencia_inicio=body.vigencia_inicio,
        ativo=True,
    )
    db.add(preco)
    db.commit()
    db.refresh(preco)
    audit_action(
        db, "preco_pdv_criado",
        user_id=current_user.id,
        tenant_id=resolve_tenant_pagador(db, current_user.id, current_user.role.nome if current_user.role else None),
        recurso_tipo="preco_pdv",
        recurso_id=preco.id,
        detalhes=f"base={body.valor_base_centavos}, adicional={body.valor_pdv_adicional_centavos}",
    )
    return preco


@router.patch("/{preco_id}", response_model=PrecoPdvResponse)
def atualizar_preco(
    preco_id: int,
    body: PrecoPdvUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    preco = db.query(PrecoPdv).filter(PrecoPdv.id == preco_id).first()
    if not preco:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preço não encontrado")
    if body.valor_base_centavos is not None:
        preco.valor_base_centavos = body.valor_base_centavos
    if body.valor_pdv_adicional_centavos is not None:
        preco.valor_pdv_adicional_centavos = body.valor_pdv_adicional_centavos
    if body.ativo is not None:
        preco.ativo = body.ativo
    db.commit()
    db.refresh(preco)
    audit_action(
        db, "preco_pdv_atualizado",
        user_id=current_user.id,
        tenant_id=resolve_tenant_pagador(db, current_user.id, current_user.role.nome if current_user.role else None),
        recurso_tipo="preco_pdv",
        recurso_id=preco.id,
    )
    return preco
