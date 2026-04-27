# PDV Ibix - API Caixas (cadastro por empresa fiscal)
"""CRUD de caixas lógicos. CA opera sobre a própria empresa fiscal."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from ...core.scope import ClienteScope, get_empresa_fiscal_empresa
from ...database.connection import get_db
from ...models import Caixa, Empresa, Usuario
from ...schemas.caixa import CaixaCreate, CaixaResponse, CaixaUpdate

router = APIRouter(prefix="/caixas", tags=["Caixas"])


def _caixa_response(db: Session, c: Caixa) -> CaixaResponse:
    emp = db.query(Empresa).filter(Empresa.id == c.empresa_id).first()
    return CaixaResponse(
        id=c.id,
        empresa_id=c.empresa_id,
        identificador=c.identificador,
        ativo=bool(c.ativo),
        created_at=c.created_at,
        updated_at=c.updated_at,
        cliente_id=(emp.cliente_id if emp else None),
    )


def _empresa_para_usuario(
    db: Session,
    current_user: Usuario,
    scope: ClienteScope,
    empresa_id: Optional[int],
) -> Empresa:
    role_nome = current_user.role.nome if current_user.role else ""
    if role_nome == "Superadministrador":
        if empresa_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe empresa_id (query) para listar ou gerenciar caixas.",
            )
        emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not emp:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        return emp
    emp = get_empresa_fiscal_empresa(db, current_user.id, role_nome)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empresa fiscal obrigatória. Configure em /fiscal/empresa",
        )
    if scope.must_filter_by_cliente() and emp.cliente_id not in (scope.allowed_ids or []):
        raise HTTPException(status_code=403, detail="Empresa fora do escopo")
    return emp


@router.get("/", response_model=List[CaixaResponse])
async def listar_caixas(
    empresa_id: Optional[int] = Query(None, description="Obrigatório para Superadministrador"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    emp = _empresa_para_usuario(db, current_user, scope, empresa_id)
    rows = db.query(Caixa).filter(Caixa.empresa_id == emp.id).order_by(Caixa.identificador).all()
    return [_caixa_response(db, r) for r in rows]


@router.get("/{caixa_id}", response_model=CaixaResponse)
async def obter_caixa(
    caixa_id: int,
    empresa_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    emp = _empresa_para_usuario(db, current_user, scope, empresa_id)
    c = db.query(Caixa).filter(Caixa.id == caixa_id, Caixa.empresa_id == emp.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    return _caixa_response(db, c)


@router.post("/", response_model=CaixaResponse, status_code=status.HTTP_201_CREATED)
async def criar_caixa(
    body: CaixaCreate,
    empresa_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    emp = _empresa_para_usuario(db, current_user, scope, empresa_id)
    ident = (body.identificador or "").strip()
    if not ident:
        raise HTTPException(status_code=400, detail="identificador é obrigatório")
    exists = (
        db.query(Caixa)
        .filter(Caixa.empresa_id == emp.id, Caixa.identificador == ident)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Já existe um caixa com este nome nesta empresa")
    c = Caixa(empresa_id=emp.id, identificador=ident, ativo=bool(body.ativo))
    db.add(c)
    db.commit()
    db.refresh(c)
    return _caixa_response(db, c)


@router.patch("/{caixa_id}", response_model=CaixaResponse)
async def atualizar_caixa(
    caixa_id: int,
    body: CaixaUpdate,
    empresa_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    emp = _empresa_para_usuario(db, current_user, scope, empresa_id)
    c = db.query(Caixa).filter(Caixa.id == caixa_id, Caixa.empresa_id == emp.id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    if body.identificador is not None:
        nid = body.identificador.strip()
        if not nid:
            raise HTTPException(status_code=400, detail="identificador inválido")
        clash = (
            db.query(Caixa)
            .filter(
                Caixa.empresa_id == emp.id,
                Caixa.identificador == nid,
                Caixa.id != caixa_id,
            )
            .first()
        )
        if clash:
            raise HTTPException(status_code=409, detail="Já existe um caixa com este nome nesta empresa")
        c.identificador = nid
    if body.ativo is not None:
        c.ativo = body.ativo
    db.commit()
    db.refresh(c)
    return _caixa_response(db, c)
