# PDV Ibix - Modelo RevisaoDirecao (ISO 17025 5.13)
from typing import TYPE_CHECKING

from sqlalchemy import Column, Date, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class RevisaoDirecao(BaseModel):
    """Registro de revisoes periodicas do sistema de gestao. Isolado por cliente (escopo)."""
    __tablename__ = "revisoes_direcao"

    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True, comment="Cliente dono do registro (escopo)")
    data_revisao = Column(Date, nullable=False)
    participantes = Column(Text, nullable=True)
    itens_analisados = Column(Text, nullable=True)
    decisoes = Column(Text, nullable=True)
    proximas_revisoes = Column(Text, nullable=True)

    cliente = relationship("Cliente", lazy="select")
