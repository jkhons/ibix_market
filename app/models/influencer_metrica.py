# PDV Ibix - Metricas de performance de influencer
"""Metricas agregadas por campanha e periodo."""
from sqlalchemy import Column, Date, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class InfluencerMetrica(BaseModel):
    __tablename__ = "influencer_metricas"

    campanha_id = Column(Integer, ForeignKey("influencer_campanhas.id", ondelete="SET NULL"), nullable=True, index=True)
    divulgador_id = Column(Integer, ForeignKey("divulgadores.id", ondelete="CASCADE"), nullable=False, index=True)
    cliques = Column(Integer, nullable=False, default=0)
    visualizacoes = Column(Integer, nullable=False, default=0)
    vendas = Column(Integer, nullable=False, default=0)
    faturamento = Column(Numeric(12, 2), nullable=False, default=0)
    conversoes_cupom = Column(Integer, nullable=False, default=0)
    periodo_inicio = Column(Date, nullable=True)
    periodo_fim = Column(Date, nullable=True)

    campanha = relationship("InfluencerCampanha", backref="metricas")
    divulgador = relationship("Divulgador", backref="metricas")

    __table_args__ = (
        Index("ix_inf_metricas_periodo", "periodo_inicio", "periodo_fim"),
        {"comment": "Metricas de performance de influencers"},
    )

    def __repr__(self):
        return f"<InfluencerMetrica(id={self.id}, vendas={self.vendas}, cliques={self.cliques})>"
