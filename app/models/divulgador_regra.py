# PDV Ibix - Regras de comissão do divulgador (Fase 2)
"""Regras: % por plano ativo, recebe 1ª parcela, percentual de comissão."""
from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class DivulgadorRegra(BaseModel):
    """Regras de comissão de um divulgador."""
    __tablename__ = "divulgador_regras"

    divulgador_id = Column(Integer, ForeignKey("divulgadores.id", ondelete="CASCADE"), nullable=False, index=True)
    percentual_plano_ativo = Column(Integer, nullable=False, default=0, comment="% sobre cada plano ativo vendido com código")
    recebe_primeira_parcela = Column(Boolean, nullable=False, default=False)
    percentual_comissao = Column(Integer, nullable=False, default=0, comment="% geral de comissão")

    divulgador = relationship("Divulgador", backref="regras")

    __table_args__ = (
        {"comment": "Regras de comissão do divulgador"},
    )

    def __repr__(self):
        return f"<DivulgadorRegra(id={self.id}, divulgador={self.divulgador_id})>"
