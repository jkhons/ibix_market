# PDV Ibix - Payment Log (Fase 3.3)
"""Auditoria de comunicação com provedores (request/response, duration)."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import Base


class PaymentLog(Base):
    """Log de chamada ao provedor: request url/headers/body, response code/body, duration_ms."""
    __tablename__ = "payment_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    transaction_id = Column(
        Integer,
        ForeignKey("payment_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider_code = Column(String(50), nullable=True)
    request_url = Column(String(512), nullable=True)
    request_headers = Column(Text, nullable=True)
    request_body = Column(Text, nullable=True)
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    transaction = relationship("PaymentTransaction", back_populates="logs")

    def __repr__(self):
        return f"<PaymentLog(id={self.id}, transaction_id={self.transaction_id}, provider_code='{self.provider_code}')>"
