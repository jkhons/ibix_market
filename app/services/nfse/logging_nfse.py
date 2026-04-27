# Persistência de log NFS-e (request/response redigido)
from typing import Optional

from sqlalchemy.orm import Session

from app.models.nfse import NfseMessageLog


def log_nfse_message(
    db: Session,
    tenant_id: int,
    nfse_invoice_id: int,
    direction: str,
    http_status: Optional[int] = None,
    payload_redacted: Optional[str] = None,
    response_redacted: Optional[str] = None,
) -> None:
    """Grava registro em nfse_message_logs (payload e response já redigidos)."""
    log = NfseMessageLog(
        tenant_id=tenant_id,
        nfse_invoice_id=nfse_invoice_id,
        direction=direction,
        http_status=http_status,
        payload_redacted=payload_redacted,
        response_redacted=response_redacted,
    )
    db.add(log)
