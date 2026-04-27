# PDV Ibix - Loja Marketplace (1:1 com estabelecimento)
from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class LojaMarketplace(BaseModel):
    """Configuração da loja do CA na plataforma (1:1 com clientes.id)."""
    __tablename__ = "lojas_marketplace"

    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status = Column(String(20), nullable=False, server_default="pendente")
    slug = Column(String(100), nullable=True, unique=True)
    nome_loja = Column(String(200), nullable=True)
    nome_fantasia = Column(String(200), nullable=True)
    categoria_principal = Column(String(120), nullable=True, index=True)
    subcategoria = Column(String(120), nullable=True)
    cidade_seo = Column(String(120), nullable=True, index=True)
    estado_seo = Column(String(2), nullable=True)
    slug_categoria_cidade = Column(String(260), nullable=True, index=True)
    seo_title = Column(String(160), nullable=True)
    seo_description = Column(String(320), nullable=True)
    og_image_url = Column(Text(), nullable=True)
    seo_enabled = Column(Boolean, nullable=False, server_default="true")
    descricao = Column(Text(), nullable=True)
    descricao_curta = Column(String(320), nullable=True)
    descricao_longa = Column(Text(), nullable=True)
    vitrine_hero_titulo_uma_linha = Column(
        Boolean, nullable=False, server_default="false"
    )
    logo_url = Column(Text(), nullable=True)
    banner_url = Column(Text(), nullable=True)
    tipo_entrega = Column(String(20), nullable=False, server_default="retirada")
    raio_entrega_km = Column(Integer, nullable=True)
    taxa_entrega_fixa = Column(Numeric(10, 2), nullable=True)
    entrega_gratis_apos = Column(Numeric(10, 2), nullable=True)
    formato_frete = Column(String(20), nullable=False, server_default="sem_frete")
    avaliacao_media = Column(Numeric(3, 2), nullable=False, server_default="0")
    total_vendas_marketplace = Column(Integer, nullable=False, server_default="0")
    faturamento_total = Column(Numeric(15, 2), nullable=False, server_default="0")

    cliente = relationship("Cliente", back_populates="loja_marketplace")
    anuncios = relationship("AnuncioPlataforma", back_populates="loja", cascade="all, delete-orphan")
    pedidos = relationship("PedidoMarketplace", back_populates="loja", cascade="all, delete-orphan")
    extratos = relationship("ExtratoLoja", back_populates="loja", cascade="all, delete-orphan")
    areas_entrega = relationship("LojaAreaEntrega", back_populates="loja", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LojaMarketplace(id={self.id}, cliente_id={self.cliente_id}, slug='{self.slug}')>"
