# PDV Ibix - Tabela de preços PDV (Fase 2 — Estrutura Comercial)
"""Preços por licença: valor base + valor por PDV adicional. Nunca hardcoded."""
from sqlalchemy import Boolean, Column, Date, Index, Integer

from ..database.base import BaseModel


class PrecoPdv(BaseModel):
    """Tabela de preços de licença PDV. Valores em centavos."""
    __tablename__ = "precos_pdv"

    valor_base_centavos = Column(Integer, nullable=False, comment="Assinatura base (inclui 1 PDV) em centavos")
    valor_pdv_adicional_centavos = Column(Integer, nullable=False, comment="Valor de cada PDV adicional em centavos")
    vigencia_inicio = Column(Date, nullable=False, comment="Data início da vigência")
    ativo = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_precos_pdv_ativo", "ativo"),
        {"comment": "Preços de licença PDV (valor_base + valor_pdv_adicional) em centavos"},
    )

    def __repr__(self):
        return f"<PrecoPdv(id={self.id}, base={self.valor_base_centavos}, adicional={self.valor_pdv_adicional_centavos})>"
