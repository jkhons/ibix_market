# PDV Ibix - Admin: Google Custom Search (credenciais + cotas por tenant)
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.admin_billing import _mask_secret, _upsert_config
from app.core.google_cse_config import (
    CHAVE_GOOGLE_CSE_API_KEY,
    CHAVE_GOOGLE_CSE_ENGINE_ID,
    CHAVE_GOOGLE_CSE_PLATAFORMA_LIMITE_DIARIO,
    CHAVE_GOOGLE_CSE_QUERY_SUFFIX,
    get_google_cse_api_key,
    get_google_cse_engine_id,
    get_google_cse_query_suffix,
    get_plataforma_limite_diario_informativo,
    google_cse_credentials_configured,
)
from app.core.middleware import require_superadmin
from app.database.connection import get_db
from app.models import GoogleCseUsoLog, Tenant

router = APIRouter(prefix="/admin/integracoes/google-cse", tags=["Admin Google CSE"])


class GoogleCseConfigResponse(BaseModel):
    engine_id: Optional[str] = None
    api_key_configured: bool
    api_key_masked: Optional[str] = None
    query_suffix: str = ""
    plataforma_limite_diario: Optional[int] = None


class GoogleCseConfigUpdate(BaseModel):
    api_key: Optional[str] = Field(None, description="Nova API Key (omitir para não alterar)")
    engine_id: Optional[str] = None
    query_suffix: Optional[str] = None
    plataforma_limite_diario: Optional[int] = Field(None, ge=0, description="Teto informacional diário (opcional)")


class TenantCseItem(BaseModel):
    tenant_id: int
    nome: str
    limite_diario: int
    uso_hoje: int
    restante: int


class ResumoCseResponse(BaseModel):
    credenciais_prontas: bool
    uso_total_hoje: int
    plataforma_limite_diario: Optional[int] = None
    tenants_com_uso_hoje: int


class TenantCsePatch(BaseModel):
    google_cse_limite_diario: int = Field(..., ge=0)


def _google_cse_config_response(db: Session) -> GoogleCseConfigResponse:
    key = get_google_cse_api_key(db)
    cx = get_google_cse_engine_id(db)
    return GoogleCseConfigResponse(
        engine_id=cx or None,
        api_key_configured=bool(key),
        api_key_masked=_mask_secret(key),
        query_suffix=get_google_cse_query_suffix(db),
        plataforma_limite_diario=get_plataforma_limite_diario_informativo(db),
    )


@router.get("/config", response_model=GoogleCseConfigResponse)
def admin_google_cse_get_config(
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    return _google_cse_config_response(db)


@router.patch("/config", response_model=GoogleCseConfigResponse)
def admin_google_cse_patch_config(
    body: GoogleCseConfigUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    if body.api_key is not None:
        _upsert_config(
            db,
            CHAVE_GOOGLE_CSE_API_KEY,
            body.api_key.strip(),
            "Google Custom Search API Key",
        )
    if body.engine_id is not None:
        _upsert_config(
            db,
            CHAVE_GOOGLE_CSE_ENGINE_ID,
            body.engine_id.strip(),
            "Google Custom Search Engine ID (cx)",
        )
    if body.query_suffix is not None:
        _upsert_config(
            db,
            CHAVE_GOOGLE_CSE_QUERY_SUFFIX,
            body.query_suffix.strip(),
            "Sufixo da query de busca de imagens (ex.: NCM ficha técnica)",
        )
    if body.plataforma_limite_diario is not None:
        _upsert_config(
            db,
            CHAVE_GOOGLE_CSE_PLATAFORMA_LIMITE_DIARIO,
            str(body.plataforma_limite_diario),
            "Teto informacional de buscas/dia na plataforma",
        )
    db.commit()
    return _google_cse_config_response(db)


@router.get("/resumo", response_model=ResumoCseResponse)
def admin_google_cse_resumo(
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    today = date.today()
    rows = db.query(Tenant).filter(Tenant.google_cse_uso_data == today).all()
    uso_total = sum(int(t.google_cse_uso_dia or 0) for t in rows)
    tenants_com_uso = len([t for t in rows if int(t.google_cse_uso_dia or 0) > 0])
    plat = get_plataforma_limite_diario_informativo(db)
    return ResumoCseResponse(
        credenciais_prontas=google_cse_credentials_configured(db),
        uso_total_hoje=uso_total,
        plataforma_limite_diario=plat,
        tenants_com_uso_hoje=tenants_com_uso,
    )


@router.get("/tenants", response_model=List[TenantCseItem])
def admin_google_cse_list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    today = date.today()
    q = db.query(Tenant).order_by(Tenant.id)
    rows = q.offset(skip).limit(limit).all()
    out: List[TenantCseItem] = []
    for t in rows:
        uso = 0
        lim = int(t.google_cse_limite_diario or 0)
        if t.google_cse_uso_data == today:
            uso = int(t.google_cse_uso_dia or 0)
        restante = max(0, lim - uso) if lim > 0 else 0
        out.append(
            TenantCseItem(
                tenant_id=t.id,
                nome=t.nome or "",
                limite_diario=lim,
                uso_hoje=uso,
                restante=restante,
            )
        )
    return out


@router.patch("/tenants/{tenant_id}", response_model=TenantCseItem)
def admin_google_cse_patch_tenant(
    tenant_id: int,
    body: TenantCsePatch,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    t.google_cse_limite_diario = body.google_cse_limite_diario
    db.commit()
    db.refresh(t)
    today = date.today()
    uso = int(t.google_cse_uso_dia or 0) if t.google_cse_uso_data == today else 0
    lim = int(t.google_cse_limite_diario or 0)
    restante = max(0, lim - uso) if lim > 0 else 0
    return TenantCseItem(
        tenant_id=t.id,
        nome=t.nome or "",
        limite_diario=lim,
        uso_hoje=uso,
        restante=restante,
    )


@router.get("/tenants/{tenant_id}/historico")
def admin_google_cse_historico(
    tenant_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_superadmin()),
):
    if not db.query(Tenant).filter(Tenant.id == tenant_id).first():
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    logs = (
        db.query(GoogleCseUsoLog)
        .filter(GoogleCseUsoLog.tenant_id == tenant_id)
        .order_by(GoogleCseUsoLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": x.id,
            "created_at": x.created_at.isoformat() if x.created_at else None,
            "usuario_id": x.usuario_id,
            "tipo": x.tipo,
        }
        for x in logs
    ]
