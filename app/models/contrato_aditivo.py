# PDV Ibix - Aditivo de contrato comercial (Fase 2)
"""Alteração formal: adicionar/remover PDVs, alterar valor."""
from sqlalchemy import Column, Date, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class ContratoAditivo(BaseModel):
    """Aditivo ao contrato comercial: registra alteração de qtd de PDVs ou valor."""
    __tablename__ = "contrato_aditivos"

    contrato_id = Column(Integer, ForeignKey("contrato_comercial.id", ondelete="CASCADE"), nullable=False, index=True)
    data_aditivo = Column(Date, nullable=False)
    qtd_pdvs_anterior = Column(Integer, nullable=False)
    qtd_pdvs_nova = Column(Integer, nullable=False)
    valor_anterior_centavos = Column(Integer, nullable=False)
    valor_novo_centavos = Column(Integer, nullable=False)
    motivo = Column(Text, nullable=True)

    contrato = relationship("ContratoComercial", back_populates="aditivos")

    __table_args__ = (
        Index("ix_contrato_aditivos_contrato_data", "contrato_id", "data_aditivo"),
        {"comment": "Aditivos ao contrato comercial SaaS"},
    )

    def __repr__(self):
        return f"<ContratoAditivo(id={self.id}, contrato={self.contrato_id}, pdvs={self.qtd_pdvs_nova})>"
