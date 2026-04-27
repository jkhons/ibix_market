# PDV Ibix - Campanha de influencer/marketing
"""Campanha vinculando influencer a loja ou plataforma."""
from sqlalchemy import Boolean, Column, Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class InfluencerCampanha(BaseModel):
    __tablename__ = "influencer_campanhas"

    divulgador_id = Column(Integer, ForeignKey("divulgadores.id", ondelete="CASCADE"), nullable=False, index=True)
    loja_id = Column(Integer, ForeignKey("lojas_marketplace.id", ondelete="SET NULL"), nullable=True, index=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    tipo = Column(String(30), nullable=False, comment="propaganda, cupom, live")
    status = Column(String(30), nullable=False, default="rascunho", comment="rascunho, ativa, pausada, finalizada, cancelada")
    data_inicio = Column(Date, nullable=True)
    data_fim = Column(Date, nullable=True)
    valor_fixo = Column(Numeric(10, 2), nullable=True)
    percentual_comissao = Column(Integer, nullable=True)
    modelo_pagamento = Column(String(30), nullable=True, comment="fixo, comissao, hibrido")
    codigo_desconto_id = Column(Integer, ForeignKey("codigos_desconto.id", ondelete="SET NULL"), nullable=True)
    is_teste = Column(Boolean, nullable=False, default=False)

    divulgador = relationship("Divulgador", backref="campanhas")
    loja = relationship("LojaMarketplace", backref="influencer_campanhas")
    codigo_desconto = relationship("CodigoDesconto", backref="influencer_campanhas")

    __table_args__ = (
        Index("ix_inf_campanhas_status", "status"),
        Index("ix_inf_campanhas_tipo", "tipo"),
        {"comment": "Campanhas de marketing com influencers"},
    )

    def __repr__(self):
        return f"<InfluencerCampanha(id={self.id}, titulo='{self.titulo}', tipo='{self.tipo}')>"
