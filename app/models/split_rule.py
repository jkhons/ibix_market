# PDV Ibix - Split Rule (Fase 3.3)
"""Regras de repasse por nível hierárquico (super_admin, admin, cliente_admin, estabelecimento)."""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class SplitRule(BaseModel):
    """Regra de split: recipient_type, recipient_id, percentage/fixed_amount, applies_to (JSON)."""
    __tablename__ = "split_rules"

    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Estabelecimento ao qual a regra se aplica",
    )
    rule_type = Column(String(30), nullable=False, comment="fixed_percentage, fixed_value, tiered")
    recipient_type = Column(String(30), nullable=False, comment="super_admin, admin, cliente_admin, estabelecimento")
    recipient_id = Column(Integer, nullable=True, comment="ID do destinatário")
    percentage = Column(Numeric(8, 4), nullable=True)
    fixed_amount = Column(Numeric(12, 2), nullable=True)
    applies_to = Column(Text, nullable=True, comment="JSON: payment_methods, min/max value")
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    cliente = relationship("Cliente", foreign_keys=[cliente_id])

    def __repr__(self):
        return f"<SplitRule(id={self.id}, cliente_id={self.cliente_id}, recipient_type='{self.recipient_type}')>"
