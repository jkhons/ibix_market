# PDV Ibix - Caixa lógico por empresa fiscal
"""N caixas por empresa (emissor fiscal). Turnos em aberturas_caixa referenciam caixa_id."""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class Caixa(BaseModel):
    __tablename__ = "caixas"

    empresa_id = Column(
        Integer,
        ForeignKey("empresa.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Empresa fiscal dona do caixa",
    )
    identificador = Column(String(80), nullable=False, comment="Nome do caixa (ex.: Balcão 1)")
    ativo = Column(Boolean, nullable=False, default=True)

    empresa = relationship("Empresa", foreign_keys=[empresa_id])
    aberturas_caixa = relationship("AberturaCaixa", back_populates="caixa", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("empresa_id", "identificador", name="uq_caixas_empresa_identificador"),
    )

    def __repr__(self):
        return f"<Caixa(id={self.id}, identificador='{self.identificador}', empresa_id={self.empresa_id})>"
