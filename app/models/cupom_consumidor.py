# PDV Ibix - Registro de uso de cupom por consumidor
from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.sql import func

from ..database.base import Base


class CupomConsumidor(Base):
    """Registro imutável de uso de cupom (sem updated_at)."""
    __tablename__ = "cupons_consumidor"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cupom_id = Column(Integer, ForeignKey("cupons_marketplace.id", ondelete="CASCADE"), nullable=False)
    consumidor_id = Column(Integer, ForeignKey("consumidores_marketplace.id", ondelete="CASCADE"), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos_marketplace.id", ondelete="SET NULL"), nullable=True)
    usado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    from sqlalchemy.orm import relationship
    cupom = relationship("CupomMarketplace", back_populates="usos")

    def __repr__(self):
        return f"<CupomConsumidor(cupom_id={self.cupom_id}, consumidor_id={self.consumidor_id})>"
