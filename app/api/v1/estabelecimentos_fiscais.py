# PDV Ibix - API Estabelecimentos Fiscais (Fase 3.1.1)
"""CRUD de estabelecimentos_fiscais. Escopo por cliente_id."""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models import AreaCliente, Empresa, EstabelecimentoFiscal, Usuario
from ...schemas.estabelecimento_fiscal import (
    EstabelecimentoFiscalCreate,
    EstabelecimentoFiscalResponse,
    EstabelecimentoFiscalUpdate,
)

router = APIRouter(prefix="/estabelecimentos-fiscais", tags=["Estabelecimentos fiscais"])


def _allowed_cliente_ids(scope: ClienteScope, db: Session, current_user: Usuario) -> Optional[List[int]]:
    if not scope.must_filter_by_cliente():
        return None
    if not scope.allowed_ids:
        return []
    if not current_user.role or current_user.role.nome != "Cliente Administrador":
        return scope.allowed_ids or []

    # CA: apenas clientes no contexto fiscal (empresa emissora), incluindo o "próprio" cliente do CA.
    ids_empresa_fiscal = {
        r[0]
        for r in db.query(Empresa.cliente_id)
        .filter(
            Empresa.cliente_id.isnot(None),
            Empresa.cliente_id.in_(scope.allowed_ids),
        )
        .distinct()
        .all()
    }
    area_own = db.query(AreaCliente.cliente_id).filter(
        AreaCliente.usuario_id == current_user.id,
        AreaCliente.ativo == True,
        AreaCliente.nome_area == "administrador",
    ).first()
    ids = set(ids_empresa_fiscal)
    if area_own and area_own[0]:
        ids.add(area_own[0])
    return [cid for cid in scope.allowed_ids if cid in ids]


@router.get("/", response_model=List[EstabelecimentoFiscalResponse])
async def listar_estabelecimentos_fiscais(
    cliente_id: Optional[int] = Query(None),
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    allowed = _allowed_cliente_ids(scope, db, current_user)
    if allowed is not None and not allowed:
        return []
    q = db.query(EstabelecimentoFiscal)
    if allowed is not None:
        q = q.filter(EstabelecimentoFiscal.cliente_id.in_(allowed))
    if cliente_id is not None:
        if allowed is not None and cliente_id not in allowed:
            raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
        q = q.filter(EstabelecimentoFiscal.cliente_id == cliente_id)
    if ativo is not None:
        q = q.filter(EstabelecimentoFiscal.ativo == ativo)
    return [EstabelecimentoFiscalResponse.model_validate(r) for r in q.order_by(EstabelecimentoFiscal.id).all()]


@router.get("/{estabelecimento_id}", response_model=EstabelecimentoFiscalResponse)
async def obter_estabelecimento_fiscal(
    estabelecimento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    e = db.query(EstabelecimentoFiscal).filter(EstabelecimentoFiscal.id == estabelecimento_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estabelecimento fiscal não encontrado")
    allowed = _allowed_cliente_ids(scope, db, current_user)
    if allowed is not None and e.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fiscal fora do escopo")
    return EstabelecimentoFiscalResponse.model_validate(e)


@router.post("/", response_model=EstabelecimentoFiscalResponse, status_code=status.HTTP_201_CREATED)
async def criar_estabelecimento_fiscal(
    body: EstabelecimentoFiscalCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    allowed = _allowed_cliente_ids(scope, db, current_user)
    if allowed is not None and body.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
    aliquotas_uf = None
    if body.aliquotas_uf is not None:
        aliquotas_uf = json.dumps(body.aliquotas_uf) if isinstance(body.aliquotas_uf, (dict, list)) else str(body.aliquotas_uf)
    e = EstabelecimentoFiscal(
        cliente_id=body.cliente_id,
        cnpj=body.cnpj,
        ie=body.ie,
        crt=body.crt,
        certificado_digital_path=body.certificado_digital_path,
        regime_tributario=body.regime_tributario,
        serie_nfe=body.serie_nfe or "1",
        aliquotas_uf=aliquotas_uf,
        ativo=body.ativo,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return EstabelecimentoFiscalResponse.model_validate(e)


@router.patch("/{estabelecimento_id}", response_model=EstabelecimentoFiscalResponse)
async def atualizar_estabelecimento_fiscal(
    estabelecimento_id: int,
    body: EstabelecimentoFiscalUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    e = db.query(EstabelecimentoFiscal).filter(EstabelecimentoFiscal.id == estabelecimento_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estabelecimento fiscal não encontrado")
    allowed = _allowed_cliente_ids(scope, db, current_user)
    if allowed is not None and e.cliente_id not in (allowed or []):
        raise HTTPException(status_code=403, detail="Estabelecimento fiscal fora do escopo")
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "aliquotas_uf" and v is not None:
            setattr(e, k, json.dumps(v) if isinstance(v, (dict, list)) else str(v))
        else:
            setattr(e, k, v)
    db.commit()
    db.refresh(e)
    return EstabelecimentoFiscalResponse.model_validate(e)


@router.delete("/{estabelecimento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_estabelecimento_fiscal(
    estabelecimento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    e = db.query(EstabelecimentoFiscal).filter(EstabelecimentoFiscal.id == estabelecimento_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estabelecimento fiscal não encontrado")
    allowed = _allowed_cliente_ids(scope, db, current_user)
    if allowed is not None and e.cliente_id not in (allowed or []):
        raise HTTPException(status_code=403, detail="Estabelecimento fiscal fora do escopo")
    db.delete(e)
    db.commit()
