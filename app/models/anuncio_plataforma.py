# PDV Ibix - Anúncio na plataforma (produto do CA publicado na vitrine)
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class AnuncioPlataforma(BaseModel):
    """Anúncio = produto do CA publicado na vitrine."""
    __tablename__ = "anuncios_plataforma"

    loja_id = Column(
        Integer,
        ForeignKey("lojas_marketplace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    produto_ca_id = Column(
        Integer,
        ForeignKey("produtos_cliente.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    categoria_id = Column(
        Integer,
        ForeignKey("categorias_plataforma.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(20), nullable=False, server_default="rascunho")
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text(), nullable=True)
    imagens = Column(Text(), nullable=True)  # JSONB em PG: sa.dialect.type_engine pode ser JSON
    preco_original = Column(Numeric(10, 2), nullable=False)
    preco_promocional = Column(Numeric(10, 2), nullable=True)
    tipo_estoque = Column(String(20), nullable=False, server_default="sincronizado")
    estoque_atual = Column(Numeric(10, 2), nullable=True)
    estoque_minimo_alerta = Column(Integer, nullable=True, server_default="5")
    variacoes = Column(Text(), nullable=True)
    atributos = Column(Text(), nullable=True)
    frete_sobrescrever_loja = Column(Boolean, nullable=False, server_default="false")
    formato_frete_produto = Column(String(20), nullable=True)
    taxa_entrega_fixa_produto = Column(Numeric(10, 2), nullable=True)
    entrega_gratis_apos_produto = Column(Numeric(10, 2), nullable=True)
    visualizacoes = Column(Integer, nullable=False, server_default="0")
    cliques = Column(Integer, nullable=False, server_default="0")
    vendas = Column(Integer, nullable=False, server_default="0")
    ultima_sincronizacao = Column(DateTime(timezone=True), nullable=True)
    # URL absoluta (CDN) de imagem OG 1.91:1 opcional; gerada/manual (Fase 02). Se null, usa galeria do anúncio.
    og_image_url = Column(String(500), nullable=True)
    custo_plataforma_estimado = Column(Numeric(10, 2), nullable=True)
    custo_cartao_estimado = Column(Numeric(10, 2), nullable=True)

    __table_args__ = (
        UniqueConstraint("loja_id", "produto_ca_id", name="uq_anuncios_plataforma_loja_produto"),
    )

    loja = relationship("LojaMarketplace", back_populates="anuncios")
    produto_cliente = relationship("ProdutoCliente", backref="anuncios_plataforma")
    categoria = relationship("CategoriaPlataforma", back_populates="anuncios")

    def __repr__(self):
        return f"<AnuncioPlataforma(id={self.id}, loja_id={self.loja_id}, titulo='{self.titulo[:30]}')>"
