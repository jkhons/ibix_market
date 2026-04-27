# PDV Ibix - API Acoes Corretivas (ISO 17025 5.11)
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.middleware import forbid_cliente_access, require_permission
from app.database.connection import get_db
from app.models.acao_corretiva import AcaoCorretiva
from app.models.processo import Processo
from app.models.usuario import Usuario
from app.schemas.acao_corretiva import (
    AcaoCorretivaCreate,
    AcaoCorretivaResponse,
    AcaoCorretivaUpdate,
)

router = APIRouter(
    prefix="/acoes-corretivas",
    tags=["Qualidade - Acoes Corretivas"],
    dependencies=[Depends(forbid_cliente_access)],
)


@router.get("/", response_model=List[AcaoCorretivaResponse])
def listar_acoes_corretivas(
    processo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("qualidade:acoes_corretivas:visualizar")),
):
    """Listar ações corretivas, opcionalmente por processo."""
    query = db.query(AcaoCorretiva).options(
        joinedload(AcaoCorretiva.processo),
        joinedload(AcaoCorretiva.responsavel),
    )
    if processo_id is not None:
        query = query.filter(AcaoCorretiva.processo_id == processo_id)
    return query.order_by(AcaoCorretiva.created_at.desc()).all()


@router.post("/", response_model=AcaoCorretivaResponse, status_code=status.HTTP_201_CREATED)
def criar_acao_corretiva(
    dados: AcaoCorretivaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("qualidade:acoes_corretivas:criar")),
):
    """Criar ação corretiva vinculada ao processo."""
    proc = db.query(Processo).filter(Processo.id == dados.processo_id).first()
    if not proc:
        raise HTTPException(status_code=404, detail="Processo nao encontrado")
    ac = AcaoCorretiva(**dados.model_dump())
    if not ac.nc_numero and proc.nc_numero:
        ac.nc_numero = proc.nc_numero
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


@router.get("/{id}", response_model=AcaoCorretivaResponse)
def obter_acao_corretiva(
    id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("qualidade:acoes_corretivas:visualizar")),
):
    """Obter ação corretiva por ID."""
    ac = db.query(AcaoCorretiva).options(
        joinedload(AcaoCorretiva.processo),
        joinedload(AcaoCorretiva.responsavel),
    ).filter(AcaoCorretiva.id == id).first()
    if not ac:
        raise HTTPException(status_code=404, detail="Acao corretiva nao encontrada")
    return ac


@router.put("/{id}", response_model=AcaoCorretivaResponse)
def atualizar_acao_corretiva(
    id: int,
    dados: AcaoCorretivaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("qualidade:acoes_corretivas:editar")),
):
    """Atualizar ação corretiva."""
    ac = db.query(AcaoCorretiva).filter(AcaoCorretiva.id == id).first()
    if not ac:
        raise HTTPException(status_code=404, detail="Acao corretiva nao encontrada")
    for k, v in dados.model_dump(exclude_unset=True).items():
        setattr(ac, k, v)
    db.commit()
    db.refresh(ac)
    return ac


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_acao_corretiva(
    id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("qualidade:acoes_corretivas:excluir")),
):
    """Excluir ação corretiva."""
    ac = db.query(AcaoCorretiva).filter(AcaoCorretiva.id == id).first()
    if not ac:
        raise HTTPException(status_code=404, detail="Acao corretiva nao encontrada")
    db.delete(ac)
    db.commit()
