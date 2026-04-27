# PDV Ibix - Modelo AcaoCorretiva (ISO 17025 5.11)
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class AcaoCorretiva(BaseModel):
    """Análise de causa raiz e ações corretivas vinculadas à NC."""
    __tablename__ = "acoes_corretivas"

    nc_numero = Column(String(50), nullable=True)
    causa_raiz = Column(Text, nullable=True)
    acao_planejada = Column(Text, nullable=False)
    responsavel_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    data_prevista = Column(Date, nullable=True)
    data_conclusao = Column(Date, nullable=True)
    eficacia_verificada = Column(Boolean, nullable=True)
    observacoes = Column(Text, nullable=True)

    responsavel = relationship("Usuario", lazy="select")
