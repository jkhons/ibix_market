# PDV Ibix - Venda Pagamento (Fase 3.2 - fracionamento)
"""Múltiplos pagamentos por venda (dinheiro + cartão + PIX, etc.)."""
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class VendaPagamento(BaseModel):
    """Um registro de pagamento de uma venda (fracionamento)."""
    __tablename__ = "venda_pagamentos"

    venda_id = Column(
        Integer,
        ForeignKey("vendas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    forma = Column(
        String(30),
        nullable=False,
        comment="dinheiro, cartao_credito, cartao_debito, pix, boleto, transferencia, vale, crediario",
    )
    valor = Column(Numeric(12, 2), nullable=False)
    status = Column(
        String(20),
        nullable=True,
        default="confirmado",
        comment="pendente, confirmado, estornado",
    )
    id_externo = Column(String(100), nullable=True, comment="ID no gateway/adquirente")
    observacao = Column(String(255), nullable=True)

    venda = relationship("Venda", back_populates="pagamentos")

    def __repr__(self):
        return f"<VendaPagamento(id={self.id}, venda_id={self.venda_id}, forma='{self.forma}', valor={self.valor})>"
