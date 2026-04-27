# PDV Ibix - Billing Usage Event (evento faturável da plataforma)
"""Eventos faturáveis: base de cobrança da plataforma (itens pagos + %). Reversão em cancelamento/refund."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import BaseModel


class BillingUsageEvent(BaseModel):
    """Evento que gera ou reverte cobrança da plataforma (idempotência por chave lógica)."""
    __tablename__ = "billing_usage_events"

    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True)
    loja_id = Column(Integer, ForeignKey("lojas_marketplace.id", ondelete="SET NULL"), nullable=True)
    pedido_id = Column(Integer, ForeignKey("pedidos_marketplace.id", ondelete="SET NULL"), nullable=True)
    payment_transaction_id = Column(Integer, ForeignKey("payment_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    provider = Column(String(50), nullable=True)
    provider_payment_id = Column(String(200), nullable=True)
    event_type = Column(String(50), nullable=False)
    item_count_billable = Column(Integer, nullable=True, server_default="0")
    gross_amount_billable = Column(Numeric(12, 2), nullable=True)
    percentage_base_amount = Column(Numeric(12, 2), nullable=True)
    is_reversal = Column(Boolean, nullable=False, server_default="false")
    source_refund_id = Column(Integer, ForeignKey("refunds.id", ondelete="SET NULL"), nullable=True)
    counted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    reversed_at = Column(DateTime(timezone=True), nullable=True)

    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    payment_transaction = relationship("PaymentTransaction", foreign_keys=[payment_transaction_id])
    source_refund = relationship("Refund", foreign_keys=[source_refund_id])

    def __repr__(self):
        return f"<BillingUsageEvent(id={self.id}, event_type='{self.event_type}', is_reversal={self.is_reversal})>"
