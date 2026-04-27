# PDV Ibix - Contratos comerciais e aditivos (Fase 2)
"""CRUD contrato_comercial + aditivos. SuperAdmin e Admin."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.audit import audit_action
from ...core.middleware import get_current_user, require_superadmin_or_admin
from ...database.connection import get_db
from ...models import SubscriptionBilling, Tenant, Usuario
from ...models.contrato_aditivo import ContratoAditivo
from ...models.contrato_comercial import ContratoComercial
from ...models.preco_pdv import PrecoPdv
from ...schemas.contrato_comercial import (
    ContratoAditivoCreate,
    ContratoAditivoResponse,
    ContratoComercialCreate,
    ContratoComercialResponse,
)

router = APIRouter(prefix="/contratos-comerciais", tags=["Contratos Comerciais"])


def _get_preco_vigente(db: Session) -> PrecoPdv:
    preco = (
        db.query(PrecoPdv)
        .filter(PrecoPdv.ativo == True)
        .order_by(PrecoPdv.vigencia_inicio.desc())
        .first()
    )
    if not preco:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nenhum preço vigente configurado. Configure em Admin > Preços PDV.",
        )
    return preco


def calcular_valor_mensal(preco: PrecoPdv, qtd_pdvs: int) -> int:
    """valor_mensal = valor_base + (qtd_pdvs - 1) * valor_pdv_adicional"""
    if qtd_pdvs <= 1:
        return preco.valor_base_centavos
    return preco.valor_base_centavos + (qtd_pdvs - 1) * preco.valor_pdv_adicional_centavos


def _sync_subscription_pdvs(db: Session, tenant_id: int, qtd_pdvs: int, valor_mensal: int) -> None:
    """Atualiza qtd_pdvs_contratados e valor_mensal_centavos na subscription do tenant."""
    sub = db.query(SubscriptionBilling).filter(SubscriptionBilling.tenant_id == tenant_id).first()
    if sub:
        sub.qtd_pdvs_contratados = qtd_pdvs
        sub.valor_mensal_centavos = valor_mensal


@router.get("/", response_model=List[ContratoComercialResponse])
def listar_contratos(
    tenant_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin_or_admin()),
):
    q = db.query(ContratoComercial)
    if tenant_id:
        q = q.filter(ContratoComercial.tenant_id == tenant_id)
    if status_filter:
        q = q.filter(ContratoComercial.status == status_filter)
    return q.order_by(ContratoComercial.created_at.desc()).all()


@router.get("/{contrato_id}", response_model=ContratoComercialResponse)
def detalhe_contrato(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin_or_admin()),
):
    contrato = db.query(ContratoComercial).filter(ContratoComercial.id == contrato_id).first()
    if not contrato:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
    return contrato


@router.post("/", response_model=ContratoComercialResponse, status_code=status.HTTP_201_CREATED)
def criar_contrato(
    body: ContratoComercialCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin_or_admin()),
):
    tenant = db.query(Tenant).filter(Tenant.id == body.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")

    existing = (
        db.query(ContratoComercial)
        .filter(ContratoComercial.tenant_id == body.tenant_id, ContratoComercial.status == "ativo")
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant já possui contrato ativo")

    preco = _get_preco_vigente(db)
    valor = calcular_valor_mensal(preco, body.qtd_pdvs_contratados)

    contrato = ContratoComercial(
        tenant_id=body.tenant_id,
        vigencia_inicio=body.vigencia_inicio,
        vigencia_fim=body.vigencia_fim,
        qtd_pdvs_contratados=body.qtd_pdvs_contratados,
        valor_mensal_centavos=valor,
        status="ativo",
    )
    db.add(contrato)
    db.flush()

    _sync_subscription_pdvs(db, body.tenant_id, body.qtd_pdvs_contratados, valor)
    db.commit()
    db.refresh(contrato)

    audit_action(
        db, "contrato_criado",
        user_id=current_user.id,
        tenant_id=body.tenant_id,
        recurso_tipo="contrato_comercial",
        recurso_id=contrato.id,
        detalhes=f"pdvs={body.qtd_pdvs_contratados}, valor={valor}",
    )
    return contrato


@router.get("/{contrato_id}/aditivos", response_model=List[ContratoAditivoResponse])
def listar_aditivos(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin_or_admin()),
):
    contrato = db.query(ContratoComercial).filter(ContratoComercial.id == contrato_id).first()
    if not contrato:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
    return (
        db.query(ContratoAditivo)
        .filter(ContratoAditivo.contrato_id == contrato_id)
        .order_by(ContratoAditivo.data_aditivo.desc())
        .all()
    )


@router.post("/{contrato_id}/aditivos", response_model=ContratoAditivoResponse, status_code=status.HTTP_201_CREATED)
def criar_aditivo(
    contrato_id: int,
    body: ContratoAditivoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin_or_admin()),
):
    contrato = db.query(ContratoComercial).filter(
        ContratoComercial.id == contrato_id,
        ContratoComercial.status == "ativo",
    ).first()
    if not contrato:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato ativo não encontrado")

    preco = _get_preco_vigente(db)
    valor_novo = calcular_valor_mensal(preco, body.qtd_pdvs_nova)

    aditivo = ContratoAditivo(
        contrato_id=contrato.id,
        data_aditivo=date.today(),
        qtd_pdvs_anterior=contrato.qtd_pdvs_contratados,
        qtd_pdvs_nova=body.qtd_pdvs_nova,
        valor_anterior_centavos=contrato.valor_mensal_centavos,
        valor_novo_centavos=valor_novo,
        motivo=body.motivo,
    )
    db.add(aditivo)

    qtd_anterior = contrato.qtd_pdvs_contratados
    contrato.qtd_pdvs_contratados = body.qtd_pdvs_nova
    contrato.valor_mensal_centavos = valor_novo

    _sync_subscription_pdvs(db, contrato.tenant_id, body.qtd_pdvs_nova, valor_novo)
    db.commit()
    db.refresh(aditivo)

    audit_action(
        db, "contrato_aditivo_criado",
        user_id=current_user.id,
        tenant_id=contrato.tenant_id,
        recurso_tipo="contrato_aditivo",
        recurso_id=aditivo.id,
        detalhes=f"pdvs {qtd_anterior}->{body.qtd_pdvs_nova}, valor {aditivo.valor_anterior_centavos}->{valor_novo}",
    )
    return aditivo
