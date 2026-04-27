# PDV Ibix - Refund (estorno)
"""Estorno total ou parcial de transação de pagamento. Auditoria e reversão de cobrança."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import BaseModel


class Refund(BaseModel):
    """Registro de estorno (total ou parcial) com trilha de quem solicitou."""
    __tablename__ = "refunds"

    payment_transaction_id = Column(Integer, ForeignKey("payment_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_code = Column(String(50), nullable=False)
    provider_refund_id = Column(String(200), nullable=True)
    refund_type = Column(String(20), nullable=False, server_default="full", comment="full, partial")
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(30), nullable=False, server_default="pending")
    reason = Column(Text, nullable=True)
    requested_by_user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    payload_json = Column(Text, nullable=True)

    payment_transaction = relationship("PaymentTransaction", back_populates="refunds")
    requested_by = relationship("Usuario", foreign_keys=[requested_by_user_id])

    def __repr__(self):
        return f"<Refund(id={self.id}, payment_transaction_id={self.payment_transaction_id}, status='{self.status}')>"
