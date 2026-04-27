# PDV Ibix - Conversas do chat marketplace (consumidor ↔ loja)
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import Base


class ConversaMarketplace(Base):
    __tablename__ = "conversas_marketplace"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    consumidor_id = Column(Integer, ForeignKey("consumidores_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    loja_id = Column(Integer, ForeignKey("lojas_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    anuncio_id = Column(Integer, ForeignKey("anuncios_plataforma.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, server_default="ativa")
    ultima_mensagem_em = Column(DateTime(timezone=True), nullable=True)

    mensagens = relationship("MensagemConversa", back_populates="conversa", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ConversaMarketplace(id={self.id}, consumidor={self.consumidor_id}, loja={self.loja_id})>"
