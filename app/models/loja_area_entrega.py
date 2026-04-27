# PDV Ibix - Área de entrega da loja (cidades atendidas)
from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class LojaAreaEntrega(BaseModel):
    """Cidade atendida pela loja. SuperAdmin configura. Taxa por cidade."""
    __tablename__ = "loja_areas_entrega"

    loja_id = Column(
        Integer,
        ForeignKey("lojas_marketplace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cidade = Column(String(100), nullable=False)
    uf = Column(String(2), nullable=False)
    codigo_ibge = Column(Integer, nullable=True)
    taxa_entrega = Column(Numeric(10, 2), nullable=False, server_default="0")
    prazo_dias = Column(Integer, nullable=True)
    ativo = Column(Boolean, nullable=False, server_default="true")

    loja = relationship("LojaMarketplace", back_populates="areas_entrega")

    __table_args__ = (
        UniqueConstraint("loja_id", "cidade", "uf", name="uq_loja_cidade_uf"),
    )

    def __repr__(self):
        return f"<LojaAreaEntrega(id={self.id}, loja_id={self.loja_id}, cidade='{self.cidade}-{self.uf}')>"
