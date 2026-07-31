# PDV Ibix — API LGPD admin (exportação/offboarding por tenant, escopo brand_id)
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.audit import audit_action
from app.core.middleware import require_superadmin
from app.core.pii_access import audit_pii_access
from app.core.rate_limiter import get_client_ip
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.services.brand_scope_service import brand_id_from_request
from app.services.lgpd_service import exportar_tenant_dados, solicitar_offboarding_tenant

router = APIRouter(prefix="/admin/lgpd", tags=["Admin LGPD"])


class TenantOffboardingRequest(BaseModel):
    confirmar: bool = Field(..., description="Deve ser true para executar offboarding")
    brand_id: Optional[int] = Field(None, description="Recorte opcional por marca")


@router.get("/tenant/{tenant_id}/export")
def admin_exportar_tenant(
    tenant_id: int,
    request: Request,
    brand_id: Optional[int] = Query(None, description="Filtrar/validar tenant nesta marca"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    """Exportação LGPD de tenant — CPF mascarado; escopo por brand_id."""
    scope_brand = brand_id if brand_id is not None else brand_id_from_request(request, db)
    try:
        dados = exportar_tenant_dados(db, tenant_id, brand_id=scope_brand)
    except ValueError as exc:
        code = str(exc)
        if code == "TENANT_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Tenant não encontrado")
        if code == "TENANT_BRAND_SCOPE":
            raise HTTPException(status_code=403, detail="Tenant não pertence à marca informada")
        raise HTTPException(status_code=400, detail=str(exc))
    audit_pii_access(
        db,
        acao="lgpd_export_tenant",
        actor=current_user,
        recurso_tipo="tenant",
        recurso_id=tenant_id,
        ip=get_client_ip(request),
        request_id=getattr(request.state, "request_id", None),
        detalhes=f"brand_id={scope_brand}",
    )
    return dados


@router.post("/tenant/{tenant_id}/offboarding")
def admin_offboarding_tenant(
    tenant_id: int,
    body: TenantOffboardingRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    """Desativa tenant para offboarding LGPD (auditável; não apaga histórico fiscal)."""
    if not body.confirmar:
        raise HTTPException(status_code=400, detail="Confirme offboarding com confirmar=true")
    scope_brand = body.brand_id if body.brand_id is not None else brand_id_from_request(request, db)
    try:
        result = solicitar_offboarding_tenant(db, tenant_id, brand_id=scope_brand)
    except ValueError as exc:
        code = str(exc)
        if code == "TENANT_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Tenant não encontrado")
        if code == "TENANT_BRAND_SCOPE":
            raise HTTPException(status_code=403, detail="Tenant não pertence à marca informada")
        raise HTTPException(status_code=400, detail=str(exc))
    audit_action(
        db,
        "lgpd_offboarding_tenant",
        user_id=current_user.id,
        tenant_id=tenant_id,
        recurso_tipo="tenant",
        recurso_id=tenant_id,
        ip=get_client_ip(request),
        request_id=getattr(request.state, "request_id", None),
        detalhes=f"brand_id={scope_brand}",
    )
    return result
