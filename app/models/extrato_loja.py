# PDV Ibix - Extrato financeiro da loja (marketplace)
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class ExtratoLoja(BaseModel):
    """Conciliação financeira do CA (marketplace)."""
    __tablename__ = "extrato_loja"

    loja_id = Column(
        Integer,
        ForeignKey("lojas_marketplace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pedido_id = Column(
        Integer,
        ForeignKey("pedidos_marketplace.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tipo = Column(String(30), nullable=False)
    descricao = Column(Text(), nullable=True)
    valor_bruto = Column(Numeric(10, 2), nullable=True)
    valor_taxa = Column(Numeric(10, 2), nullable=True)
    valor_liquido = Column(Numeric(10, 2), nullable=True)
    valor_frete_cliente = Column(Numeric(10, 2), nullable=True)
    saldo_anterior = Column(Numeric(10, 2), nullable=True)
    saldo_atual = Column(Numeric(10, 2), nullable=True)
    status = Column(String(20), nullable=False, server_default="pendente")
    data_disponivel = Column(DateTime(timezone=True), nullable=True)
    data_pagamento = Column(DateTime(timezone=True), nullable=True)
    comprovante = Column(Text(), nullable=True)

    loja = relationship("LojaMarketplace", back_populates="extratos")

    def __repr__(self):
        return f"<ExtratoLoja(id={self.id}, loja_id={self.loja_id}, tipo='{self.tipo}')>"
