# PDV Ibix - Movimento de Caixa (Fase 3.2 - sangria/suprimento)
"""Sangria e suprimento por abertura de caixa. Senha conforme MAPA_RBAC."""
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class MovimentoCaixa(BaseModel):
    """Movimento de caixa: sangria ou suprimento em uma abertura de caixa."""
    __tablename__ = "movimentos_caixa"

    abertura_caixa_id = Column(
        Integer,
        ForeignKey("aberturas_caixa.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo = Column(
        String(20),
        nullable=False,
        comment="sangria, suprimento",
    )
    valor = Column(Numeric(12, 2), nullable=False)
    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    observacao = Column(String(255), nullable=True)

    abertura_caixa = relationship("AberturaCaixa", back_populates="movimentos_caixa")
    usuario = relationship("Usuario", foreign_keys=[usuario_id])

    def __repr__(self):
        return f"<MovimentoCaixa(id={self.id}, abertura_caixa_id={self.abertura_caixa_id}, tipo='{self.tipo}', valor={self.valor})>"
