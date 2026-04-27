# PDV Ibix - Log de acessos (visitantes) com classificação tipo_visitante
# Append-only: cada requisição HTTP registra IP, user_agent, tipo_visitante
from sqlalchemy import Column, DateTime, Index, Integer, String
from sqlalchemy.sql import func

from ..database.base import Base


class AccessLog(Base):
    """Registro de acesso (visitante) com classificação HUMANO/BOT/CLOUD."""
    __tablename__ = "access_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    tipo_visitante = Column(String(10), nullable=False, index=True)  # HUMANO, BOT, CLOUD
    path = Column(String(512), nullable=True)

    __table_args__ = (
        Index("ix_access_log_created_at", "created_at"),
        # tipo_visitante já tem index=True na coluna
        {"comment": "Log de acessos com classificação de visitante (HUMANO/BOT/CLOUD)"},
    )

    def __repr__(self):
        return f"<AccessLog(id={self.id}, tipo='{self.tipo_visitante}', ip='{self.ip}')>"
