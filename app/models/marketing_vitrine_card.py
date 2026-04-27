# PDV Ibix — Cards de marketing da vitrine (destaques / oferta_semana)
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class MarketingVitrineCard(BaseModel):
    __tablename__ = "marketing_vitrine_cards"

    tipo_bloco = Column(String(20), nullable=False, index=True)
    tipo_card = Column(String(20), nullable=False)
    titulo = Column(String(200), nullable=True)
    descricao = Column(Text(), nullable=True)
    imagem_url = Column(Text(), nullable=True)
    link_url = Column(Text(), nullable=True)
    anuncio_id = Column(Integer, ForeignKey("anuncios_plataforma.id", ondelete="SET NULL"), nullable=True, index=True)
    anuncio_ids = Column(JSONB, nullable=True)
    # Apenas tipo_card=cabecalho_ofertas: quantos itens (livre/anúncio) exibir na seção.
    limite_exibicao = Column(Integer, nullable=True)
    # Apenas cabecalho_ofertas: clientes.id dos tenants (CA); vazio/null = todas as lojas.
    cliente_ids = Column(JSONB, nullable=True)
    embaralhar_produtos = Column(Boolean, nullable=True)
    somente_com_desconto = Column(Boolean, nullable=True)
    ordem = Column(Integer, nullable=False, server_default="100")
    ativo = Column(Boolean, nullable=False, server_default="true")
    inicio_em = Column(DateTime(timezone=True), nullable=True)
    fim_em = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)

    anuncio = relationship("AnuncioPlataforma", foreign_keys=[anuncio_id])
