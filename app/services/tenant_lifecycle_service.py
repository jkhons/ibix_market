# PDV Ibix — Ciclo de vida do tenant (Fase 9 enterprise)
"""Provisionamento, suspensão, retomada e offboarding auditável por brand_id/tenant_id."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.tenant import Tenant


def _assert_tenant_brand(tenant: Tenant, brand_id: Optional[int]) -> None:
    if brand_id is not None and tenant.brand_id != brand_id:
        raise ValueError("TENANT_BRAND_SCOPE")


def get_tenant_lifecycle_status(db: Session, tenant_id: int, *, brand_id: Optional[int] = None) -> dict:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise ValueError("TENANT_NOT_FOUND")
    _assert_tenant_brand(tenant, brand_id)

    from app.models.subscription_billing import SubscriptionBilling

    sub = (
        db.query(SubscriptionBilling)
        .filter(SubscriptionBilling.tenant_id == tenant_id)
        .order_by(SubscriptionBilling.id.desc())
        .first()
    )
    estado = "ativo" if tenant.ativo else "suspenso"
    if sub and getattr(sub, "status", None) == "bloqueada":
        estado = "bloqueado_billing"

    return {
        "tenant_id": tenant.id,
        "brand_id": tenant.brand_id,
        "nome": tenant.nome,
        "slug": tenant.slug,
        "ativo": tenant.ativo,
        "estado": estado,
        "subscription_status": getattr(sub, "status", None) if sub else None,
        "offboarding_solicitado_em": getattr(tenant, "offboarding_solicitado_em", None),
    }


def suspender_tenant(
    db: Session,
    tenant_id: int,
    *,
    brand_id: Optional[int] = None,
    motivo: str = "",
) -> dict:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise ValueError("TENANT_NOT_FOUND")
    _assert_tenant_brand(tenant, brand_id)
    tenant.ativo = False
    db.commit()
    return {
        "tenant_id": tenant_id,
        "acao": "suspender",
        "ativo": False,
        "motivo": motivo or None,
        "em": datetime.now(timezone.utc).isoformat(),
    }


def retomar_tenant(db: Session, tenant_id: int, *, brand_id: Optional[int] = None) -> dict:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise ValueError("TENANT_NOT_FOUND")
    _assert_tenant_brand(tenant, brand_id)
    tenant.ativo = True
    db.commit()
    return {
        "tenant_id": tenant_id,
        "acao": "retomar",
        "ativo": True,
        "em": datetime.now(timezone.utc).isoformat(),
    }


def solicitar_offboarding_tenant_lifecycle(
    db: Session,
    tenant_id: int,
    *,
    brand_id: Optional[int] = None,
) -> dict:
    """Desativa tenant e marca timestamp de offboarding (dados fiscais retidos por política legal)."""
    from app.services.lgpd_service import solicitar_offboarding_tenant

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise ValueError("TENANT_NOT_FOUND")
    _assert_tenant_brand(tenant, brand_id)

    result = solicitar_offboarding_tenant(db, tenant_id, brand_id=brand_id)
    now = datetime.now(timezone.utc)
    if hasattr(tenant, "offboarding_solicitado_em"):
        tenant.offboarding_solicitado_em = now
        db.commit()
    result["offboarding_solicitado_em"] = now.isoformat()
    result["acao"] = "offboarding"
    result["retencao_fiscal"] = (
        "Dados fiscais e vendas mantidos conforme obrigação legal (5 anos). "
        "Exclusão física requer processo auditado pós-retention."
    )
    return result
