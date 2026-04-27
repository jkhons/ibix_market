# PDV Ibix - API Produtos-Fornecedor (vínculos produto ↔ fornecedor)
"""Listagem e remoção de vínculos ProdutoFornecedor. Escopo por cliente_id do fornecedor."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.audit import audit_action
from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from ...core.scope import ClienteScope, resolve_tenant_pagador
from ...database.connection import get_db
from ...models import FornecedorCliente, ProdutoCliente, ProdutoFornecedor, Usuario
from ...schemas.produto_fornecedor import ProdutoFornecedorResponse

router = APIRouter(prefix="/produtos-fornecedor", tags=["Produtos Fornecedor (vínculo)"])


def _allowed_cliente_ids(scope: ClienteScope) -> Optional[List[int]]:
    if not scope.must_filter_by_cliente():
        return None
    return scope.allowed_ids or []


def _resolve_tenant(db: Session, user: Usuario) -> Optional[int]:
    return resolve_tenant_pagador(db, user.id, user.role.nome if user.role else None)


def _ensure_fornecedor_in_scope(db: Session, fornecedor_cliente_id: int, scope: ClienteScope) -> FornecedorCliente:
    """Carrega fornecedor e valida que está no escopo do usuário."""
    f = db.query(FornecedorCliente).filter(FornecedorCliente.id == fornecedor_cliente_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and f.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Fornecedor fora do escopo")
    return f


@router.get("/", response_model=List[ProdutoFornecedorResponse])
async def listar_produtos_fornecedor(
    fornecedor_cliente_id: int = Query(..., description="ID do fornecedor"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    _ensure_fornecedor_in_scope(db, fornecedor_cliente_id, scope)
    rows = (
        db.query(ProdutoFornecedor, ProdutoCliente.nome, ProdutoCliente.codigo)
        .outerjoin(ProdutoCliente, ProdutoCliente.id == ProdutoFornecedor.produto_cliente_id)
        .filter(ProdutoFornecedor.fornecedor_cliente_id == fornecedor_cliente_id)
        .order_by(ProdutoFornecedor.codigo_fornecedor)
        .all()
    )
    out: List[ProdutoFornecedorResponse] = []
    for pf, prod_nome, prod_codigo in rows:
        base = ProdutoFornecedorResponse.model_validate(pf)
        out.append(
            base.model_copy(update={"produto_nome": prod_nome, "produto_codigo": prod_codigo})
        )
    return out


@router.delete("/{vinculo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_vinculo(
    vinculo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    pf = db.query(ProdutoFornecedor).filter(ProdutoFornecedor.id == vinculo_id).first()
    if not pf:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")
    _ensure_fornecedor_in_scope(db, pf.fornecedor_cliente_id, scope)
    pf_id = pf.id
    forn_id = pf.fornecedor_cliente_id
    prod_id = pf.produto_cliente_id
    cod = pf.codigo_fornecedor
    db.delete(pf)
    db.commit()
    audit_action(
        db, "produto_fornecedor_excluido",
        user_id=current_user.id,
        tenant_id=_resolve_tenant(db, current_user),
        recurso_tipo="produto_fornecedor", recurso_id=pf_id,
        detalhes=f"fornecedor_id={forn_id} produto_id={prod_id} cod={cod}",
    )
    return None
