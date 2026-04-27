# PDV Ibix - Status de repasse (transações modo plataforma)
"""Lista global de status para controle de repasse por transação."""
from sqlalchemy import Boolean, Column, Integer, String

from ..database.base import BaseModel


class RepasseStatus(BaseModel):
    """Status de repasse: Aguardando, Feito, Cancelado, etc. Sigla com 5 caracteres para badge."""
    __tablename__ = "status_repasse"

    nome = Column(String(100), nullable=False)
    sigla = Column(String(5), nullable=False, unique=True, index=True)
    ordem = Column(Integer, nullable=False, server_default="0")
    ativo = Column(Boolean, nullable=False, server_default="true")

    def __repr__(self):
        return f"<RepasseStatus(id={self.id}, sigla='{self.sigla}', nome='{self.nome}')>"
