# PDV Ibix - API Fornecedores por Estabelecimento (Fase 2)
"""CRUD de fornecedores_cliente. Escopo por cliente_id. Validação CNPJ + anti-duplicata + auditoria."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.audit import audit_action
from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from ...core.scope import ClienteScope, resolve_tenant_pagador
from ...database.connection import get_db
from ...models import FornecedorCliente, Usuario
from ...schemas.fornecedor_cliente import FornecedorClienteCreate, FornecedorClienteResponse, FornecedorClienteUpdate

router = APIRouter(prefix="/fornecedores-cliente", tags=["Fornecedores (estabelecimento)"])


def _allowed_cliente_ids(scope: ClienteScope) -> Optional[List[int]]:
    if not scope.must_filter_by_cliente():
        return None
    return scope.allowed_ids or []


def _resolve_tenant(db: Session, user: Usuario) -> Optional[int]:
    return resolve_tenant_pagador(db, user.id, user.role.nome if user.role else None)


def _check_cnpj_duplicata(db: Session, cliente_id: int, cnpj: Optional[str], excluir_id: Optional[int] = None) -> None:
    """Rejeita 409 se já existe fornecedor com mesmo CNPJ no estabelecimento."""
    if not cnpj:
        return
    q = db.query(FornecedorCliente).filter(
        FornecedorCliente.cliente_id == cliente_id,
        FornecedorCliente.cnpj == cnpj,
    )
    if excluir_id is not None:
        q = q.filter(FornecedorCliente.id != excluir_id)
    existente = q.first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe fornecedor com CNPJ {cnpj} neste estabelecimento (ID {existente.id}: {existente.nome})",
        )


@router.get("/", response_model=List[FornecedorClienteResponse])
async def listar_fornecedores(
    cliente_id: Optional[int] = Query(None),
    ativo: Optional[bool] = None,
    busca: Optional[str] = Query(None, description="Busca por nome ou CNPJ"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and not allowed:
        return []
    q = db.query(FornecedorCliente)
    if allowed is not None:
        q = q.filter(FornecedorCliente.cliente_id.in_(allowed))
    if cliente_id is not None:
        if allowed is not None and cliente_id not in allowed:
            raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
        q = q.filter(FornecedorCliente.cliente_id == cliente_id)
    if ativo is not None:
        q = q.filter(FornecedorCliente.ativo == ativo)
    if busca:
        termo = f"%{busca.strip()}%"
        q = q.filter(
            FornecedorCliente.nome.ilike(termo) | FornecedorCliente.cnpj.ilike(termo)
        )
    return [FornecedorClienteResponse.model_validate(r) for r in q.order_by(FornecedorCliente.nome).all()]


@router.get("/{fornecedor_id}", response_model=FornecedorClienteResponse)
async def obter_fornecedor(
    fornecedor_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    f = db.query(FornecedorCliente).filter(FornecedorCliente.id == fornecedor_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and f.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Fornecedor fora do escopo")
    return FornecedorClienteResponse.model_validate(f)


@router.post("/", response_model=FornecedorClienteResponse, status_code=status.HTTP_201_CREATED)
async def criar_fornecedor(
    body: FornecedorClienteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and body.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
    _check_cnpj_duplicata(db, body.cliente_id, body.cnpj)
    f = FornecedorCliente(
        cliente_id=body.cliente_id,
        nome=body.nome,
        cnpj=body.cnpj,
        contato=body.contato,
        email=body.email,
        telefone=body.telefone,
        ativo=body.ativo,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    audit_action(
        db, "fornecedor_criado",
        user_id=current_user.id,
        tenant_id=_resolve_tenant(db, current_user),
        recurso_tipo="fornecedor_cliente", recurso_id=f.id,
        detalhes=f"nome={f.nome} cnpj={f.cnpj or ''} cliente_id={f.cliente_id}",
    )
    return FornecedorClienteResponse.model_validate(f)


@router.patch("/{fornecedor_id}", response_model=FornecedorClienteResponse)
async def atualizar_fornecedor(
    fornecedor_id: int,
    body: FornecedorClienteUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    f = db.query(FornecedorCliente).filter(FornecedorCliente.id == fornecedor_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and f.cliente_id not in (allowed or []):
        raise HTTPException(status_code=403, detail="Fornecedor fora do escopo")
    updates = body.model_dump(exclude_unset=True)
    if "cnpj" in updates and updates["cnpj"]:
        _check_cnpj_duplicata(db, f.cliente_id, updates["cnpj"], excluir_id=f.id)
    for k, v in updates.items():
        setattr(f, k, v)
    db.commit()
    db.refresh(f)
    audit_action(
        db, "fornecedor_atualizado",
        user_id=current_user.id,
        tenant_id=_resolve_tenant(db, current_user),
        recurso_tipo="fornecedor_cliente", recurso_id=f.id,
        detalhes=f"campos={list(updates.keys())}",
    )
    return FornecedorClienteResponse.model_validate(f)


@router.delete("/{fornecedor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_fornecedor(
    fornecedor_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    f = db.query(FornecedorCliente).filter(FornecedorCliente.id == fornecedor_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and f.cliente_id not in (allowed or []):
        raise HTTPException(status_code=403, detail="Fornecedor fora do escopo")
    nome_log = f.nome
    fid_log = f.id
    cid_log = f.cliente_id
    db.delete(f)
    db.commit()
    audit_action(
        db, "fornecedor_excluido",
        user_id=current_user.id,
        tenant_id=_resolve_tenant(db, current_user),
        recurso_tipo="fornecedor_cliente", recurso_id=fid_log,
        detalhes=f"nome={nome_log} cliente_id={cid_log}",
    )
    return None
