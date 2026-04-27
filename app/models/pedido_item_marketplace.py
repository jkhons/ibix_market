# PDV Ibix - Item do pedido marketplace
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class PedidoItemMarketplace(BaseModel):
    """Item do pedido da loja (evitar conflito com pedido_itens)."""
    __tablename__ = "pedido_itens_marketplace"

    tenant_id = Column(Integer, nullable=False, index=True)
    pedido_id = Column(
        Integer,
        ForeignKey("pedidos_marketplace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    loja_id = Column(Integer, nullable=False, index=True)
    anuncio_id = Column(
        Integer,
        ForeignKey("anuncios_plataforma.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    produto_id = Column(Integer, nullable=True, index=True)
    sku_id = Column(Integer, nullable=True)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Numeric(10, 2), nullable=False)
    desconto_unitario = Column(Numeric(10, 2), nullable=False, server_default="0")
    preco_total = Column(Numeric(10, 2), nullable=False)
    variacao_selecionada = Column(Text(), nullable=True)
    nome_produto_snapshot = Column(String(255), nullable=False)
    categoria_snapshot = Column(String(120), nullable=True)
    marca_snapshot = Column(String(120), nullable=True)
    sku_snapshot = Column(String(120), nullable=True)
    formato_frete_item_snapshot = Column(String(20), nullable=True)
    origem_frete_item_snapshot = Column(String(20), nullable=True)
    taxa_entrega_item = Column(Numeric(10, 2), nullable=True)

    pedido = relationship("PedidoMarketplace", back_populates="itens")
    anuncio = relationship("AnuncioPlataforma", backref="pedido_itens_marketplace")

    def __repr__(self):
        return f"<PedidoItemMarketplace(id={self.id}, pedido_id={self.pedido_id}, anuncio_id={self.anuncio_id})>"
