# PDV Ibix — API ciclo de vida do tenant (Fase 9 — Superadmin)
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.audit import audit_action
from app.core.middleware import require_superadmin
from app.core.rate_limiter import get_client_ip
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.services.brand_scope_service import brand_id_from_request
from app.services.tenant_lifecycle_service import (
    get_tenant_lifecycle_status,
    retomar_tenant,
    solicitar_offboarding_tenant_lifecycle,
    suspender_tenant,
)

router = APIRouter(prefix="/admin/tenant-lifecycle", tags=["Admin Tenant Lifecycle"])


class SuspendTenantRequest(BaseModel):
    motivo: str = Field("", max_length=500)
    brand_id: Optional[int] = None


class OffboardingLifecycleRequest(BaseModel):
    confirmar: bool = Field(..., description="Deve ser true")
    brand_id: Optional[int] = None


def _handle_value_error(exc: ValueError) -> None:
    code = str(exc)
    if code == "TENANT_NOT_FOUND":
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    if code == "TENANT_BRAND_SCOPE":
        raise HTTPException(status_code=403, detail="Tenant não pertence à marca informada")
    raise HTTPException(status_code=400, detail=str(exc))


@router.get("/tenant/{tenant_id}/status")
def admin_tenant_lifecycle_status(
    tenant_id: int,
    request: Request,
    brand_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    scope_brand = brand_id if brand_id is not None else brand_id_from_request(request, db)
    try:
        return get_tenant_lifecycle_status(db, tenant_id, brand_id=scope_brand)
    except ValueError as exc:
        _handle_value_error(exc)


@router.post("/tenant/{tenant_id}/suspend")
def admin_suspend_tenant(
    tenant_id: int,
    body: SuspendTenantRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    scope_brand = body.brand_id if body.brand_id is not None else brand_id_from_request(request, db)
    try:
        result = suspender_tenant(db, tenant_id, brand_id=scope_brand, motivo=body.motivo)
    except ValueError as exc:
        _handle_value_error(exc)
    audit_action(
        db,
        "tenant_suspend",
        user_id=current_user.id,
        tenant_id=tenant_id,
        recurso_tipo="tenant",
        recurso_id=tenant_id,
        ip=get_client_ip(request),
        request_id=getattr(request.state, "request_id", None),
        detalhes=f"brand_id={scope_brand}; motivo={body.motivo[:200]}",
    )
    return result


@router.post("/tenant/{tenant_id}/resume")
def admin_resume_tenant(
    tenant_id: int,
    request: Request,
    brand_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    scope_brand = brand_id if brand_id is not None else brand_id_from_request(request, db)
    try:
        result = retomar_tenant(db, tenant_id, brand_id=scope_brand)
    except ValueError as exc:
        _handle_value_error(exc)
    audit_action(
        db,
        "tenant_resume",
        user_id=current_user.id,
        tenant_id=tenant_id,
        recurso_tipo="tenant",
        recurso_id=tenant_id,
        ip=get_client_ip(request),
        request_id=getattr(request.state, "request_id", None),
        detalhes=f"brand_id={scope_brand}",
    )
    return result


@router.post("/tenant/{tenant_id}/offboarding")
def admin_offboarding_lifecycle(
    tenant_id: int,
    body: OffboardingLifecycleRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    if not body.confirmar:
        raise HTTPException(status_code=400, detail="Confirme offboarding com confirmar=true")
    scope_brand = body.brand_id if body.brand_id is not None else brand_id_from_request(request, db)
    try:
        result = solicitar_offboarding_tenant_lifecycle(db, tenant_id, brand_id=scope_brand)
    except ValueError as exc:
        _handle_value_error(exc)
    audit_action(
        db,
        "tenant_offboarding",
        user_id=current_user.id,
        tenant_id=tenant_id,
        recurso_tipo="tenant",
        recurso_id=tenant_id,
        ip=get_client_ip(request),
        request_id=getattr(request.state, "request_id", None),
        detalhes=f"brand_id={scope_brand}",
    )
    return result
