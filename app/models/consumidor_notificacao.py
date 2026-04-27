# PDV Ibix - Notificações in-app para consumidor mobile
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from ..database.base import Base


class ConsumidorNotificacao(Base):
    """Notificação persistente no inbox do app mobile."""
    __tablename__ = "consumidor_notificacoes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    consumidor_id = Column(Integer, ForeignKey("consumidores_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(50), nullable=False, index=True)
    titulo = Column(String(255), nullable=False)
    mensagem = Column(Text, nullable=False)
    dados_json = Column(JSONB, nullable=True)
    lida = Column(Boolean, nullable=False, server_default="false")

    def __repr__(self):
        return f"<ConsumidorNotificacao(id={self.id}, tipo={self.tipo}, lida={self.lida})>"
