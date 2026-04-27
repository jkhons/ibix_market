# PDV Ibix - Billing events (webhook idempotente) - E4.1/E5.4
from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from ..database.base import Base


class BillingEvent(Base):
    """Eventos de billing recebidos por webhook (idempotencia por webhook_id)."""
    __tablename__ = "billing_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    webhook_id = Column(String(128), nullable=False, unique=True, index=True)
    payload = Column(Text, nullable=True)
    assinatura_recebida = Column(String(256), nullable=True)
    status = Column(String(32), nullable=False, default="recebido", index=True)
    erro_detalhe = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_billing_events_status_created", "status", "created_at"),
        {"comment": "Webhook billing: idempotencia + assinatura"},
    )

    def __repr__(self):
        return f"<BillingEvent(id={self.id}, webhook_id='{self.webhook_id}', status='{self.status}')>"
