# PDV Ibix - Evento de status do pedido (histórico/timeline para o comprador)
# Sem updated_at; apenas created_at para auditoria.
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import Base


class PedidoStatusEvento(Base):
    """Evento de status do pedido marketplace (pedido_criado, pagamento_aprovado, preparando, enviado, etc.)."""
    __tablename__ = "pedido_status_eventos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pedido_id = Column(
        Integer,
        ForeignKey("pedidos_marketplace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_evento = Column(String(50), nullable=False)  # pedido_criado, pagamento_aprovado, status_alterado
    status_codigo = Column(String(30), nullable=True)  # aguardando_pagamento, confirmado, preparando, enviado...
    status_label = Column(String(100), nullable=True)  # label amigável (ex: "Preparando")
    actor_type = Column(String(30), nullable=False, server_default="sistema")  # sistema, loja, webhook
    actor_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    pedido = relationship("PedidoMarketplace", back_populates="status_eventos")

    def __repr__(self):
        return f"<PedidoStatusEvento(id={self.id}, pedido_id={self.pedido_id}, tipo='{self.tipo_evento}', status='{self.status_codigo}')>"
