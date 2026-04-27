# PDV Ibix - API Revisoes Direcao (ISO 17025 5.13)
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.middleware import forbid_cliente_access, get_cliente_scope_dep, require_permission
from app.core.scope import ClienteScope
from app.database.connection import get_db
from app.models.revisao_direcao import RevisaoDirecao
from app.models.usuario import Usuario
from app.schemas.revisao_direcao import (
    RevisaoDirecaoCreate,
    RevisaoDirecaoResponse,
    RevisaoDirecaoUpdate,
)

router = APIRouter(
    prefix="/revisoes-direcao",
    tags=["Qualidade - Revisao Direcao"],
    dependencies=[Depends(forbid_cliente_access)],
)


@router.get("/", response_model=List[RevisaoDirecaoResponse])
def listar(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("qualidade:revisoes_direcao:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    q = db.query(RevisaoDirecao)
    if scope.must_filter_by_cliente():
        if not scope.allowed_ids:
            return []
        q = q.filter(RevisaoDirecao.cliente_id.in_(scope.allowed_ids))
    return q.order_by(RevisaoDirecao.data_revisao.desc()).all()


@router.post("/", response_model=RevisaoDirecaoResponse, status_code=status.HTTP_201_CREATED)
def criar(
    dados: RevisaoDirecaoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("qualidade:revisoes_direcao:criar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    if scope.must_filter_by_cliente() and dados.cliente_id is not None and dados.cliente_id not in scope.allowed_ids:
        raise HTTPException(status_code=403, detail="Cliente fora do seu escopo de acesso")
    obj = RevisaoDirecao(**dados.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{id}", response_model=RevisaoDirecaoResponse)
def obter(
    id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("qualidade:revisoes_direcao:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    obj = db.query(RevisaoDirecao).filter(RevisaoDirecao.id == id).first()
    if not obj:
        raise HTTPException(404, "Revisao nao encontrada")
    if scope.must_filter_by_cliente():
        if not scope.allowed_ids or obj.cliente_id not in scope.allowed_ids:
            raise HTTPException(404, "Revisao nao encontrada")
    return obj


@router.put("/{id}", response_model=RevisaoDirecaoResponse)
def atualizar(
    id: int,
    dados: RevisaoDirecaoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("qualidade:revisoes_direcao:editar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    obj = db.query(RevisaoDirecao).filter(RevisaoDirecao.id == id).first()
    if not obj:
        raise HTTPException(404, "Revisao nao encontrada")
    if scope.must_filter_by_cliente():
        if not scope.allowed_ids or obj.cliente_id not in scope.allowed_ids:
            raise HTTPException(404, "Revisao nao encontrada")
    for k, v in dados.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("qualidade:revisoes_direcao:excluir")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    obj = db.query(RevisaoDirecao).filter(RevisaoDirecao.id == id).first()
    if not obj:
        raise HTTPException(404, "Revisao nao encontrada")
    if scope.must_filter_by_cliente():
        if not scope.allowed_ids or obj.cliente_id not in scope.allowed_ids:
            raise HTTPException(404, "Revisao nao encontrada")
    db.delete(obj)
    db.commit()
