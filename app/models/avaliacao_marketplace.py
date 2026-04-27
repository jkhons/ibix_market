# PDV Ibix - Avaliação pós-compra (marketplace)
from sqlalchemy import Column, ForeignKey, Integer, String, Text

from ..database.base import BaseModel


class AvaliacaoMarketplace(BaseModel):
    """Avaliações pós-compra na loja."""
    __tablename__ = "avaliacoes_marketplace"

    pedido_id = Column(
        Integer,
        ForeignKey("pedidos_marketplace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    anuncio_id = Column(
        Integer,
        ForeignKey("anuncios_plataforma.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    loja_id = Column(
        Integer,
        ForeignKey("lojas_marketplace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    comprador_nome = Column(String(200), nullable=True)
    nota = Column(Integer, nullable=False)
    comentario = Column(Text(), nullable=True)
    resposta_loja = Column(Text(), nullable=True)
    imagens = Column(Text(), nullable=True)

    def __repr__(self):
        return f"<AvaliacaoMarketplace(id={self.id}, anuncio_id={self.anuncio_id}, nota={self.nota})>"
