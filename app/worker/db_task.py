# PDV Ibix — Sessão DB para workers Celery (Fase 9 enterprise)
"""Workers usam open_db_session com bypass explícito ou tenant_id — nunca SessionLocal cru."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy.orm import Session


@contextmanager
def worker_db_session(
    *,
    tenant_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    bypass_rls: Optional[bool] = None,
) -> Iterator[Session]:
    """
    Sessão com SET LOCAL (timeout + RLS).

    - Job de plataforma (sem tenant_id): bypass_rls=True quando RLS_ENABLED.
    - Job escopado: informe tenant_id (e brand_id se aplicável), bypass_rls=False.
    """
    from app.core.rls import rls_enabled
    from app.database.connection import open_db_session

    if bypass_rls is None:
        bypass_rls = tenant_id is None and rls_enabled()

    db = open_db_session(
        tenant_id=tenant_id,
        brand_id=brand_id,
        bypass_rls=bypass_rls,
    )
    try:
        yield db
    finally:
        db.close()
