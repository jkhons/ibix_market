# PDV Ibix - API Planos, Módulos e Entitlements (SaaS)
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from ...core.middleware import get_current_user
from ...database.connection import get_db
from ...models import Module, Plan, TenantEntitlement, Usuario
from ...schemas.saas import (
    EntitlementsListResponse,
    ModuleResponse,
    PlanResponse,
    TenantEntitlementResponse,
)

router = APIRouter(tags=["SaaS - Planos e Módulos"])


@router.get("/plans", response_model=List[PlanResponse])
def list_plans(
    db: Session = Depends(get_db),
    ativo_only: bool = Query(True, description="Apenas planos ativos"),
):
    """Lista planos disponíveis (catálogo). Público para UI de assinatura."""
    q = db.query(Plan)
    if ativo_only:
        q = q.filter(Plan.ativo == True)
    return q.order_by(Plan.nome).all()


@router.get("/modules", response_model=List[ModuleResponse])
def list_modules(
    db: Session = Depends(get_db),
    ativo_only: bool = Query(True, description="Apenas módulos ativos"),
):
    """Lista módulos do sistema (catálogo). Público para UI de assinatura."""
    q = db.query(Module)
    if ativo_only:
        q = q.filter(Module.ativo == True)
    return q.order_by(Module.nome).all()


@router.get("/tenants/current/entitlements", response_model=EntitlementsListResponse)
def get_current_entitlements(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Retorna os entitlements (módulos e status/limits) do tenant do usuário logado.
    Se o usuário não tiver tenant_id, retorna lista vazia (comportamento compatível).
    """
    if not current_user.tenant_id:
        return EntitlementsListResponse(tenant_id=None, entitlements=[])

    ents = (
        db.query(TenantEntitlement)
        .options(joinedload(TenantEntitlement.module))
        .filter(
            TenantEntitlement.tenant_id == current_user.tenant_id,
            TenantEntitlement.status == "ativo",
        )
        .all()
    )
    list_response = [
        TenantEntitlementResponse(
            module_id=e.module_id,
            module_slug=e.module.slug,
            module_nome=e.module.nome,
            status=e.status,
            limits=e.limits,
            vigencia_inicio=e.vigencia_inicio,
            vigencia_fim=e.vigencia_fim,
        )
        for e in ents
    ]
    return EntitlementsListResponse(
        tenant_id=current_user.tenant_id,
        entitlements=list_response,
    )
