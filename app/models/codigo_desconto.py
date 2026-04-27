# PDV Ibix - Código de desconto (Fase 2)
"""Códigos de promoção vinculados a divulgadores."""
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class CodigoDesconto(BaseModel):
    """Código de desconto/promoção."""
    __tablename__ = "codigos_desconto"

    codigo = Column(String(50), nullable=False, unique=True, index=True)
    tipo_promocao = Column(String(50), nullable=False, comment="desconto_primeira_parcela, desconto_mensalidade, trial_estendido")
    desconto_primeira_parcela_percent = Column(Integer, nullable=False, default=0, comment="% desconto na 1ª parcela")
    desconto_mensalidade_percent = Column(Integer, nullable=False, default=0, comment="% desconto na mensalidade")
    meses_desconto = Column(Integer, nullable=True, comment="Meses de vigência do desconto (null=indefinido)")
    ativo = Column(Boolean, nullable=False, default=True)
    divulgador_id = Column(Integer, ForeignKey("divulgadores.id", ondelete="SET NULL"), nullable=True, index=True)

    divulgador = relationship("Divulgador", backref="codigos_desconto")

    __table_args__ = (
        Index("ix_codigos_desconto_ativo", "ativo"),
        {"comment": "Códigos de desconto/promoção"},
    )

    def __repr__(self):
        return f"<CodigoDesconto(id={self.id}, codigo='{self.codigo}')>"
