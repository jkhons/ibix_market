# PDV Ibix - Modelo Abertura de Caixa (turno por caixa lógico)
"""Uma abertura de caixa = um turno em um caixa cadastrado. Vendas vinculam abertura_caixa_id."""
import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class StatusAberturaCaixa(str, enum.Enum):
    ABERTA = "aberta"
    FECHADA = "fechada"


class AberturaCaixa(BaseModel):
    """Turno de caixa. Um caixa pode ter várias aberturas ao longo do tempo; só uma aberta por vez."""
    __tablename__ = "aberturas_caixa"

    caixa_id = Column(
        Integer,
        ForeignKey("caixas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Caixa lógico em que o turno foi aberto",
    )
    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Operador que abriu o caixa",
    )
    data_abertura = Column(DateTime(timezone=True), nullable=False, comment="Data/hora abertura")
    data_fechamento = Column(DateTime(timezone=True), nullable=True, comment="Data/hora fechamento")
    valor_inicial = Column(Numeric(12, 2), nullable=False, default=0, comment="Valor inicial do caixa")
    valor_final = Column(Numeric(12, 2), nullable=True, comment="Valor ao fechar")
    status = Column(
        String(20),
        nullable=False,
        default=StatusAberturaCaixa.ABERTA.value,
        comment="aberta, fechada",
    )

    caixa = relationship("Caixa", back_populates="aberturas_caixa")
    usuario = relationship("Usuario", foreign_keys=[usuario_id])
    movimentos_caixa = relationship("MovimentoCaixa", back_populates="abertura_caixa", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AberturaCaixa(id={self.id}, caixa_id={self.caixa_id}, status='{self.status}')>"
