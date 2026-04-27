# PDV Ibix - API Aberturas de Caixa (turno por caixa lógico)
"""Abertura e fechamento de caixa por caixa cadastrado. Escopo via empresa do caixa."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ...core.audit import audit_action
from ...core.middleware import get_cliente_scope_dep, get_current_user
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models import AberturaCaixa, Caixa, Empresa, MovimentoCaixa, Usuario, Venda
from ...models.abertura_caixa import StatusAberturaCaixa
from ...schemas.abertura_caixa import AberturaCaixaAbrir, AberturaCaixaFechar, AberturaCaixaResponse

router = APIRouter(prefix="/aberturas-caixa", tags=["Caixa (turno)"])

ROLES_CAIXA = ("Superadministrador", "Administrador", "Cliente Administrador", "Operador PDV")


def _role_ok(user: Usuario) -> bool:
    role_nome = user.role.nome if user.role else None
    return role_nome in ROLES_CAIXA


def _empresa_do_caixa(db: Session, caixa: Caixa) -> Optional[Empresa]:
    return db.query(Empresa).filter(Empresa.id == caixa.empresa_id).first()


def _can_access_caixa(scope: ClienteScope, caixa: Caixa, role_nome: Optional[str], db: Session) -> bool:
    if role_nome == "Operador PDV":
        return True
    if not scope.must_filter_by_cliente():
        return True
    emp = _empresa_do_caixa(db, caixa)
    if not emp or emp.cliente_id is None:
        return False
    return (scope.allowed_ids or []) and emp.cliente_id in scope.allowed_ids


@router.get("/", response_model=dict)
async def listar_aberturas(
    caixa_id: Optional[int] = Query(None, description="Filtrar por caixa"),
    status_filter: Optional[str] = Query(None, alias="status", description="aberta | fechada"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista aberturas de caixa com paginação. Retorna {items, total, skip, limit}."""
    if not _role_ok(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para acessar caixa")
    role_nome = current_user.role.nome if current_user.role else None

    q = db.query(AberturaCaixa).options(joinedload(AberturaCaixa.caixa))
    if caixa_id is not None:
        cx = db.query(Caixa).filter(Caixa.id == caixa_id).first()
        if not cx:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caixa não encontrado")
        if not _can_access_caixa(scope, cx, role_nome, db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Caixa fora do escopo")
        q = q.filter(AberturaCaixa.caixa_id == caixa_id)
    else:
        if scope.must_filter_by_cliente() and role_nome != "Operador PDV":
            allowed = scope.allowed_ids or []
            if not allowed:
                return {"items": [], "total": 0, "skip": skip, "limit": limit}
            q = q.join(Caixa).join(Empresa).filter(Empresa.cliente_id.in_(allowed))
    if status_filter:
        q = q.filter(AberturaCaixa.status == status_filter)
    total = q.count()
    rows = q.order_by(AberturaCaixa.data_abertura.desc()).offset(skip).limit(limit).all()
    return {
        "items": [AberturaCaixaResponse.model_validate(r) for r in rows],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/caixa-aberta", response_model=Optional[AberturaCaixaResponse])
async def obter_caixa_aberta(
    caixa_id: int = Query(..., description="ID do caixa cadastrado"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Retorna a abertura de caixa aberta do caixa, se houver. Usado para vincular venda ao turno."""
    if not _role_ok(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para acessar caixa")
    cx = db.query(Caixa).filter(Caixa.id == caixa_id).first()
    if not cx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caixa não encontrado")
    role_nome = current_user.role.nome if current_user.role else None
    if not _can_access_caixa(scope, cx, role_nome, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Caixa fora do escopo")
    ab = (
        db.query(AberturaCaixa)
        .filter(AberturaCaixa.caixa_id == caixa_id, AberturaCaixa.status == StatusAberturaCaixa.ABERTA.value)
        .first()
    )
    return AberturaCaixaResponse.model_validate(ab) if ab else None


@router.get("/{abertura_id}/resumo", response_model=dict)
async def resumo_turno(
    abertura_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Totais do turno: vendas, troco (soma), sangria/suprimento."""
    if not _role_ok(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")
    ab = db.query(AberturaCaixa).filter(AberturaCaixa.id == abertura_id).first()
    if not ab:
        raise HTTPException(status_code=404, detail="Abertura de caixa não encontrada")
    cx = db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
    if not cx:
        raise HTTPException(status_code=404, detail="Caixa não encontrado")
    role_nome = current_user.role.nome if current_user.role else None
    if not _can_access_caixa(scope, cx, role_nome, db):
        raise HTTPException(status_code=403, detail="Abertura fora do escopo")

    n_vendas = db.query(func.count(Venda.id)).filter(Venda.abertura_caixa_id == abertura_id).scalar() or 0
    sum_total = db.query(func.coalesce(func.sum(Venda.total), 0)).filter(Venda.abertura_caixa_id == abertura_id).scalar()
    sum_troco = db.query(func.coalesce(func.sum(Venda.troco), 0)).filter(Venda.abertura_caixa_id == abertura_id).scalar()
    movs = db.query(MovimentoCaixa).filter(MovimentoCaixa.abertura_caixa_id == abertura_id).all()
    sangria = sum(float(m.valor) for m in movs if m.tipo == "sangria")
    suprimento = sum(float(m.valor) for m in movs if m.tipo == "suprimento")
    return {
        "abertura_caixa_id": abertura_id,
        "caixa_id": cx.id,
        "caixa_identificador": cx.identificador,
        "quantidade_vendas": int(n_vendas),
        "soma_total_vendas": float(sum_total or 0),
        "soma_troco_vendas": float(sum_troco or 0),
        "total_sangria": sangria,
        "total_suprimento": suprimento,
    }


@router.get("/{abertura_id}", response_model=AberturaCaixaResponse)
async def obter_abertura(
    abertura_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Obtém uma abertura de caixa por ID."""
    if not _role_ok(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para acessar caixa")
    ab = db.query(AberturaCaixa).filter(AberturaCaixa.id == abertura_id).first()
    if not ab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Abertura de caixa não encontrada")
    cx = db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
    if not cx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caixa não encontrado")
    role_nome = current_user.role.nome if current_user.role else None
    if not _can_access_caixa(scope, cx, role_nome, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Abertura fora do escopo")
    return AberturaCaixaResponse.model_validate(ab)


@router.post("/abrir", response_model=AberturaCaixaResponse, status_code=status.HTTP_201_CREATED)
async def abrir_caixa(
    body: AberturaCaixaAbrir,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Abre caixa (iniciar turno). Só é possível uma abertura aberta por caixa."""
    if not _role_ok(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para abrir caixa")
    cx = db.query(Caixa).filter(Caixa.id == body.caixa_id).first()
    if not cx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caixa não encontrado")
    if not cx.ativo:
        raise HTTPException(status_code=400, detail="Caixa inativo não pode abrir turno")
    role_nome = current_user.role.nome if current_user.role else None
    if not _can_access_caixa(scope, cx, role_nome, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Caixa fora do escopo")
    aberta = (
        db.query(AberturaCaixa)
        .filter(
            AberturaCaixa.caixa_id == body.caixa_id,
            AberturaCaixa.status == StatusAberturaCaixa.ABERTA.value,
        )
        .first()
    )
    if aberta:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe turno aberto neste caixa. Feche o turno atual antes de abrir outro.",
        )
    valor = body.valor_inicial if body.valor_inicial is not None else Decimal("0")
    ab = AberturaCaixa(
        caixa_id=body.caixa_id,
        usuario_id=current_user.id,
        data_abertura=datetime.now(timezone.utc),
        valor_inicial=valor,
        status=StatusAberturaCaixa.ABERTA.value,
    )
    db.add(ab)
    db.commit()
    db.refresh(ab)
    audit_action(
        db,
        "caixa_aberta",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="abertura_caixa",
        recurso_id=ab.id,
        detalhes=f"caixa_id={body.caixa_id} valor_inicial={valor}",
    )
    return AberturaCaixaResponse.model_validate(ab)


@router.patch("/{abertura_id}/fechar", response_model=AberturaCaixaResponse)
async def fechar_caixa(
    abertura_id: int,
    body: AberturaCaixaFechar,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Fecha caixa (encerra turno): define valor_final, data_fechamento e status fechada."""
    if not _role_ok(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para fechar caixa")
    ab = db.query(AberturaCaixa).filter(AberturaCaixa.id == abertura_id).first()
    if not ab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Abertura de caixa não encontrada")
    if ab.status == StatusAberturaCaixa.FECHADA.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Caixa já está fechada")
    cx = db.query(Caixa).filter(Caixa.id == ab.caixa_id).first()
    if not cx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caixa não encontrado")
    role_nome = current_user.role.nome if current_user.role else None
    if not _can_access_caixa(scope, cx, role_nome, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Abertura fora do escopo")
    ab.data_fechamento = datetime.now(timezone.utc)
    ab.valor_final = body.valor_final
    ab.status = StatusAberturaCaixa.FECHADA.value
    db.commit()
    db.refresh(ab)
    audit_action(
        db,
        "caixa_fechada",
        user_id=current_user.id,
        tenant_id=getattr(current_user, "tenant_id", None),
        recurso_tipo="abertura_caixa",
        recurso_id=abertura_id,
        detalhes=f"valor_final={body.valor_final}",
    )
    return AberturaCaixaResponse.model_validate(ab)
