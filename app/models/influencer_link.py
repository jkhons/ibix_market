# PDV Ibix - Link rastreavel de influencer
"""Link com codigo de rastreio para tracking de cliques e conversoes."""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class InfluencerLink(BaseModel):
    __tablename__ = "influencer_links"

    campanha_id = Column(Integer, ForeignKey("influencer_campanhas.id", ondelete="SET NULL"), nullable=True, index=True)
    divulgador_id = Column(Integer, ForeignKey("divulgadores.id", ondelete="CASCADE"), nullable=False, index=True)
    url_destino = Column(String(1000), nullable=False)
    codigo_rastreio = Column(String(100), nullable=False, unique=True, index=True)
    ativo = Column(Boolean, nullable=False, default=True)

    campanha = relationship("InfluencerCampanha", backref="links")
    divulgador = relationship("Divulgador", backref="links_rastreaveis")

    __table_args__ = (
        {"comment": "Links rastreaveis de influencers"},
    )

    def __repr__(self):
        return f"<InfluencerLink(id={self.id}, codigo='{self.codigo_rastreio}')>"
