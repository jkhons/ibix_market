# PDV Ibix - Pagamento MP (rastreio por assinatura)
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class Payment(BaseModel):
    """Rastreio de pagamentos Mercado Pago por assinatura."""
    __tablename__ = "payments"

    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    mp_payment_id = Column(BigInteger, nullable=False)
    status = Column(String(20), nullable=False, index=True)
    amount_centavos = Column(Integer, nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    external_reference = Column(String(128), nullable=True, index=True)
    payer_user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    raw_json = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("mp_payment_id", name="uq_payments_mp_payment_id"),
        Index("ix_payments_subscription_status", "subscription_id", "status"),
        {"comment": "Pagamentos MP por assinatura (rastreio e auditoria)"},
    )

    subscription = relationship("SubscriptionBilling", backref="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, mp_payment_id={self.mp_payment_id}, status='{self.status}')>"
