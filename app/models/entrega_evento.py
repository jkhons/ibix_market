# PDV Ibix - Evento de entrega (histórico/timeline)
# Sem updated_at; apenas created_at para auditoria.
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import Base


class EntregaEvento(Base):
    """Evento da entrega (entrega_criada, entrega_publicada, entrega_aceita, etc.)."""
    __tablename__ = "entrega_eventos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    entrega_id = Column(Integer, ForeignKey("entregas_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_evento = Column(String(50), nullable=False)
    actor_type = Column(String(30), nullable=False)  # sistema, tenant_usuario, entregador
    actor_id = Column(Integer, nullable=True)
    payload_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    entrega = relationship("EntregaMarketplace", back_populates="eventos")

    def __repr__(self):
        return f"<EntregaEvento(id={self.id}, entrega_id={self.entrega_id}, tipo='{self.tipo_evento}')>"
