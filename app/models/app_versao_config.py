# PDV Ibix - Controle de versão do app mobile (force update / soft update)
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from ..database.base import Base


class AppVersaoConfig(Base):
    """Uma linha por plataforma (ios / android). Controla versão mínima e recomendada."""
    __tablename__ = "app_versao_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    plataforma = Column(String(10), nullable=False, unique=True)
    versao_minima = Column(String(20), nullable=False, server_default="1.0.0")
    versao_recomendada = Column(String(20), nullable=False, server_default="1.0.0")
    url_loja = Column(String(500), nullable=True)
    mensagem = Column(Text, nullable=True)

    def __repr__(self):
        return f"<AppVersaoConfig(plataforma={self.plataforma}, min={self.versao_minima}, rec={self.versao_recomendada})>"
