# PDV Ibix - Anti-spam de notificações (e-mail/WhatsApp)
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint

from ..database.base import BaseModel


class BillingNotificacao(BaseModel):
    """Registro de notificação enviada por tenant e tipo (evita reenvio)."""
    __tablename__ = "billing_notificacoes"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(32), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=False)
    canal = Column(String(20), nullable=False, default="email")

    __table_args__ = (
        UniqueConstraint("tenant_id", "tipo", name="uq_billing_notificacoes_tenant_tipo"),
        Index("ix_billing_notificacoes_tenant_tipo", "tenant_id", "tipo"),
        {"comment": "Anti-spam: notificações enviadas por tenant e tipo (trial_d7, pastdue_d7, etc.)"},
    )

    def __repr__(self):
        return f"<BillingNotificacao(id={self.id}, tenant_id={self.tenant_id}, tipo='{self.tipo}')>"
