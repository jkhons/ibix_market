# PDV Ibix - Favoritos (wishlist) do consumidor
from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.sql import func

from ..database.base import Base


class ConsumidorFavorito(Base):
    """Favorito = consumidor marcou um anúncio para acompanhar."""
    __tablename__ = "consumidor_favoritos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    consumidor_id = Column(Integer, ForeignKey("consumidores_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    anuncio_id = Column(Integer, ForeignKey("anuncios_plataforma.id", ondelete="CASCADE"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("consumidor_id", "anuncio_id", name="uq_consumidor_favoritos_consumidor_anuncio"),
    )

    def __repr__(self):
        return f"<ConsumidorFavorito(id={self.id}, consumidor_id={self.consumidor_id}, anuncio_id={self.anuncio_id})>"
