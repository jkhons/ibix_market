# PDV Ibix - Idempotência e auditoria de webhooks (MP + multi-gateway)
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text, UniqueConstraint

from ..database.base import BaseModel


class WebhookEvent(BaseModel):
    """Eventos de webhook por provider (idempotência por event_key). Trilha técnica completa para auditoria."""
    __tablename__ = "webhook_events"

    provider = Column(String(32), nullable=False, default="mercadopago", index=True)
    event_key = Column(String(128), nullable=False)
    event_type = Column(String(64), nullable=True)
    provider_event_id = Column(String(128), nullable=True)
    provider_payment_id = Column(String(128), nullable=True)
    payment_transaction_id = Column(Integer, nullable=True)
    subscription_payment_id = Column(Integer, nullable=True)
    signature_valid = Column(Boolean, nullable=True)
    normalized_status = Column(String(50), nullable=True)
    headers_json = Column(Text, nullable=True)
    query_params_json = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    raw_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_attempts = Column(Integer, nullable=True, server_default="0")
    last_processing_error = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("provider", "event_key", name="uq_webhook_events_provider_event_key"),
        Index("ix_webhook_events_provider_received", "provider", "received_at"),
        {"comment": "Idempotência webhook (provider + event_key); auditoria técnica"},
    )

    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, provider='{self.provider}', event_key='{self.event_key}')>"
