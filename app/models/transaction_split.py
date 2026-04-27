# PDV Ibix - Transaction Split (Fase 3.3)
"""Valores distribuídos por transação (receita por nível hierárquico)."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class TransactionSplit(BaseModel):
    """Split: recipient_type, recipient_id, original_amount, fee_amount, net_amount, status, settled_at."""
    __tablename__ = "transaction_splits"

    transaction_id = Column(
        Integer,
        ForeignKey("payment_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_type = Column(String(30), nullable=False)
    recipient_id = Column(Integer, nullable=True)
    original_amount = Column(Numeric(12, 2), nullable=False)
    fee_amount = Column(Numeric(12, 2), nullable=False, default=0)
    net_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), nullable=False, default="pending", comment="pending, settled, failed")
    settled_at = Column(DateTime(timezone=True), nullable=True)

    transaction = relationship("PaymentTransaction", back_populates="splits")

    def __repr__(self):
        return f"<TransactionSplit(id={self.id}, transaction_id={self.transaction_id}, net_amount={self.net_amount})>"
