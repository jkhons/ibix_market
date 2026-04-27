# PDV Ibix - Cupom de desconto do marketplace
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class CupomMarketplace(BaseModel):
    __tablename__ = "cupons_marketplace"

    codigo = Column(String(50), nullable=False, unique=True)
    tipo_desconto = Column(String(20), nullable=False)  # percentual | fixo
    valor_desconto = Column(Numeric(10, 2), nullable=False)
    valor_minimo_pedido = Column(Numeric(10, 2), nullable=True)
    uso_maximo = Column(Integer, nullable=True)
    uso_atual = Column(Integer, nullable=False, server_default="0")
    uso_maximo_por_consumidor = Column(Integer, nullable=True, server_default="1")
    valido_de = Column(DateTime(timezone=True), nullable=True)
    valido_ate = Column(DateTime(timezone=True), nullable=True)
    ativo = Column(Boolean, nullable=False, server_default="true")
    loja_id = Column(Integer, ForeignKey("lojas_marketplace.id", ondelete="SET NULL"), nullable=True, index=True)
    criado_por = Column(Integer, nullable=True)

    usos = relationship("CupomConsumidor", back_populates="cupom", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CupomMarketplace(id={self.id}, codigo={self.codigo}, tipo={self.tipo_desconto})>"
