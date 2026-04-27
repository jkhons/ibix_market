# PDV Ibix - Mensagens de chat dentro de uma conversa
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import Base


class MensagemConversa(Base):
    __tablename__ = "mensagens_conversa"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    conversa_id = Column(Integer, ForeignKey("conversas_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    remetente_tipo = Column(String(20), nullable=False)  # consumidor | loja
    remetente_id = Column(Integer, nullable=False)
    texto = Column(Text, nullable=True)
    imagem_url = Column(String(500), nullable=True)
    lida = Column(Boolean, nullable=False, server_default="false")

    conversa = relationship("ConversaMarketplace", back_populates="mensagens")

    def __repr__(self):
        return f"<MensagemConversa(id={self.id}, conversa={self.conversa_id}, tipo={self.remetente_tipo})>"
