# PDV Ibix - Termos buscados para autocomplete e populares
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from ..database.base import Base


class TermoBuscado(Base):
    __tablename__ = "termos_buscados"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    termo = Column(String(255), nullable=False, unique=True)
    contagem = Column(Integer, nullable=False, server_default="1")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<TermoBuscado(termo='{self.termo}', contagem={self.contagem})>"
