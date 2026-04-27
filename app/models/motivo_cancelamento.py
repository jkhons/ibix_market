# PDV Ibix - Motivos de cancelamento e devolução (tabela de domínio)
from sqlalchemy import Boolean, Column, Integer, String

from ..database.base import Base


class MotivoCancelamento(Base):
    """Motivo pré-definido — tipo: 'cancelamento' ou 'devolucao'."""
    __tablename__ = "motivos_cancelamento"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    descricao = Column(String(255), nullable=False)
    tipo = Column(String(20), nullable=False, index=True)
    ativo = Column(Boolean, nullable=False, server_default="true")
    ordem = Column(Integer, nullable=False, server_default="0")

    def __repr__(self):
        return f"<MotivoCancelamento(id={self.id}, tipo={self.tipo}, desc='{self.descricao[:30]}')>"
