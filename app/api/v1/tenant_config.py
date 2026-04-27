# PDV Ibix - API config do tenant (ex.: cupom)
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.billing import _ensure_ca_tenant_and_subscription
from app.core.middleware import AuthMiddleware, forbid_cliente_access
from app.database.connection import get_db
from app.models import Tenant, Usuario
from app.schemas.cupom import TenantCupomConfigResponse, TenantCupomConfigUpdate

router = APIRouter(prefix="/tenant-config", tags=["Tenant config"])


def _tenant_id_from_user(user: Usuario) -> Optional[int]:
    return getattr(user, "tenant_id", None)


@router.get("/cupom", response_model=TenantCupomConfigResponse)
def get_tenant_cupom_config(
    db=Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Retorna a configuração de cupom do tenant do usuário (modo impressão e tipo)."""
    tenant_id = _tenant_id_from_user(current_user)
    if not tenant_id:
        tenant_id = _ensure_ca_tenant_and_subscription(db, current_user)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant não identificado")
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")
    return TenantCupomConfigResponse(
        cupom_impressao_modo=getattr(tenant, "cupom_impressao_modo", None),
        cupom_tipo=getattr(tenant, "cupom_tipo", None),
        cupom_fiscal_emissor=getattr(tenant, "cupom_fiscal_emissor", None),
    )


@router.patch("/cupom", response_model=TenantCupomConfigResponse)
def update_tenant_cupom_config(
    body: TenantCupomConfigUpdate,
    db=Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Atualiza a configuração de cupom do tenant. Apenas CA, Admin ou SuperAdmin."""
    role = (current_user.role.nome if current_user.role else "") or ""
    if role not in ("Superadministrador", "Administrador", "Cliente Administrador"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas Super Admin, Administrador ou Cliente Administrador podem alterar a config de cupom.",
        )
    tenant_id = _tenant_id_from_user(current_user)
    if not tenant_id:
        tenant_id = _ensure_ca_tenant_and_subscription(db, current_user)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant não identificado")
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")
    if body.cupom_impressao_modo is not None:
        tenant.cupom_impressao_modo = body.cupom_impressao_modo if body.cupom_impressao_modo in ("automatico", "manual") else None
    if body.cupom_tipo is not None:
        tenant.cupom_tipo = body.cupom_tipo if body.cupom_tipo in ("nao_fiscal", "fiscal") else None
    if body.cupom_fiscal_emissor is not None:
        tenant.cupom_fiscal_emissor = body.cupom_fiscal_emissor if body.cupom_fiscal_emissor in ("interno", "externo") else None
    db.commit()
    db.refresh(tenant)
    return TenantCupomConfigResponse(
        cupom_impressao_modo=tenant.cupom_impressao_modo,
        cupom_tipo=tenant.cupom_tipo,
        cupom_fiscal_emissor=tenant.cupom_fiscal_emissor,
    )
