# PDV Ibix - Histórico de eventos do webhook WhatsApp (Meta)
from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from ..database.base import Base


class WhatsappWebhookEvent(Base):
    """Eventos recebidos do webhook WhatsApp (Meta) para histórico e auditoria."""
    __tablename__ = "whatsapp_webhook_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    payload = Column(Text, nullable=True)
    tipo_evento = Column(String(64), nullable=True, index=True)  # message, status, etc.
    from_phone = Column(String(32), nullable=True, index=True)

    __table_args__ = (
        Index("ix_whatsapp_webhook_events_created_at", "created_at"),
        {"comment": "Histórico webhook WhatsApp (Meta)"},
    )

    def __repr__(self):
        return f"<WhatsappWebhookEvent(id={self.id}, tipo={self.tipo_evento})>"
