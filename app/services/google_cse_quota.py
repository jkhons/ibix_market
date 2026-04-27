# PDV Ibix - Cota diária Google Custom Search por tenant
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import GoogleCseUsoLog, Tenant


def _reset_day_if_needed(tenant: Tenant, today: date) -> None:
    if tenant.google_cse_uso_data != today:
        tenant.google_cse_uso_dia = 0
        tenant.google_cse_uso_data = today


def reserve_search_quota(db: Session, tenant_id: int) -> None:
    """
    Reserva 1 busca (incrementa uso) com lock no tenant.
    Se a chamada ao Google falhar depois, chamar release_search_quota.
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).with_for_update().first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")
    today = date.today()
    _reset_day_if_needed(tenant, today)
    if int(tenant.google_cse_limite_diario or 0) <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Busca de imagens (Google) não liberada para este estabelecimento. Solicite ao administrador da plataforma.",
        )
    if int(tenant.google_cse_uso_dia or 0) >= int(tenant.google_cse_limite_diario):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Cota diária de buscas de imagens esgotada. Tente amanhã ou solicite liberação ao administrador.",
        )
    tenant.google_cse_uso_dia = int(tenant.google_cse_uso_dia or 0) + 1
    db.flush()


def release_search_quota(db: Session, tenant_id: int) -> None:
    """Reverte uma reserva quando a chamada ao Google falha."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).with_for_update().first()
    if not tenant:
        return
    today = date.today()
    _reset_day_if_needed(tenant, today)
    tenant.google_cse_uso_dia = max(0, int(tenant.google_cse_uso_dia or 0) - 1)
    db.flush()


def log_search_success(db: Session, tenant_id: int, usuario_id: int) -> None:
    db.add(GoogleCseUsoLog(tenant_id=tenant_id, usuario_id=usuario_id, tipo="search"))
    db.flush()
