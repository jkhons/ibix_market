# PDV Ibix - Reserva de estoque do marketplace
"""Reserva de estoque por pedido marketplace. Status: reserved -> committed (pago) ou released (cancelado/expirado)."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import BaseModel


class ReservaEstoqueMarketplace(BaseModel):
    """Reserva de quantidade de anúncio/produto para um pedido da loja. Baixa definitiva só após pagamento."""
    __tablename__ = "reserva_estoque_marketplace"

    pedido_id = Column(Integer, ForeignKey("pedidos_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    pedido_item_id = Column(Integer, ForeignKey("pedido_itens_marketplace.id", ondelete="SET NULL"), nullable=True)
    produto_cliente_id = Column(Integer, ForeignKey("produtos_cliente.id", ondelete="SET NULL"), nullable=True)
    anuncio_id = Column(Integer, ForeignKey("anuncios_plataforma.id", ondelete="CASCADE"), nullable=False)
    quantidade = Column(Numeric(12, 3), nullable=False)
    status = Column(String(30), nullable=False, server_default="reserved", comment="reserved, committed, released")
    reserved_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reserved_until = Column(DateTime(timezone=True), nullable=True)
    committed_at = Column(DateTime(timezone=True), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)

    pedido = relationship("PedidoMarketplace", back_populates="reservas_estoque")
    pedido_item = relationship("PedidoItemMarketplace", foreign_keys=[pedido_item_id])
    anuncio = relationship("AnuncioPlataforma", foreign_keys=[anuncio_id])

    def __repr__(self):
        return f"<ReservaEstoqueMarketplace(id={self.id}, pedido_id={self.pedido_id}, status='{self.status}')>"
