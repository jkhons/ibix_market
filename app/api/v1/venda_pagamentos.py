# PDV Ibix - API Venda Pagamentos (Fase 3.2 - fracionamento)
"""Listar e criar pagamentos por venda. Escopo via venda.cliente_id."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models import Usuario, Venda, VendaPagamento
from ...schemas.venda_pagamento import VendaPagamentoCreate, VendaPagamentoResponse

router = APIRouter(prefix="/venda-pagamentos", tags=["Venda pagamentos (fracionamento)"])


def _allowed_cliente_ids(scope: ClienteScope) -> Optional[List[int]]:
    if not scope.must_filter_by_cliente():
        return None
    return scope.allowed_ids or []


def _venda_no_escopo(db: Session, venda_id: int, scope: ClienteScope) -> Optional[Venda]:
    v = db.query(Venda).filter(Venda.id == venda_id).first()
    if not v:
        return None
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and (v.cliente_id is None or v.cliente_id not in allowed):
        return None
    return v


@router.get("/", response_model=List[VendaPagamentoResponse])
async def listar_pagamentos(
    venda_id: int = Query(..., description="ID da venda"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    v = _venda_no_escopo(db, venda_id, scope)
    if not v:
        raise HTTPException(status_code=404, detail="Venda não encontrada ou fora do escopo")
    rows = db.query(VendaPagamento).filter(VendaPagamento.venda_id == venda_id).order_by(VendaPagamento.id).all()
    return [VendaPagamentoResponse.model_validate(r) for r in rows]


@router.post("/", response_model=VendaPagamentoResponse, status_code=status.HTTP_201_CREATED)
async def criar_pagamento(
    body: VendaPagamentoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    v = _venda_no_escopo(db, body.venda_id, scope)
    if not v:
        raise HTTPException(status_code=404, detail="Venda não encontrada ou fora do escopo")
    p = VendaPagamento(
        venda_id=body.venda_id,
        forma=body.forma,
        valor=body.valor,
        status=body.status or "confirmado",
        id_externo=body.id_externo,
        observacao=body.observacao,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return VendaPagamentoResponse.model_validate(p)


@router.get("/{pagamento_id}", response_model=VendaPagamentoResponse)
async def obter_pagamento(
    pagamento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    p = db.query(VendaPagamento).filter(VendaPagamento.id == pagamento_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    v = _venda_no_escopo(db, p.venda_id, scope)
    if not v:
        raise HTTPException(status_code=404, detail="Venda não encontrada ou fora do escopo")
    return VendaPagamentoResponse.model_validate(p)
