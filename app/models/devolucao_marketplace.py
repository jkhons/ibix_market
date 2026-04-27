# PDV Ibix - Devoluções e reembolsos do marketplace
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class DevolucaoMarketplace(BaseModel):
    __tablename__ = "devolucoes_marketplace"

    pedido_id = Column(Integer, ForeignKey("pedidos_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    consumidor_id = Column(Integer, ForeignKey("consumidores_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    motivo_id = Column(Integer, ForeignKey("motivos_cancelamento.id", ondelete="SET NULL"), nullable=True)
    descricao = Column(Text, nullable=True)
    tipo = Column(String(20), nullable=False)  # devolucao | reembolso
    status = Column(String(20), nullable=False, server_default="aberta", index=True)
    fotos_json = Column(JSONB, nullable=True)
    valor_reembolso = Column(Numeric(10, 2), nullable=True)
    resposta_loja = Column(Text, nullable=True)
    respondido_por = Column(Integer, nullable=True)
    respondido_em = Column(DateTime(timezone=True), nullable=True)

    pedido = relationship("PedidoMarketplace")
    motivo = relationship("MotivoCancelamento")

    def __repr__(self):
        return f"<DevolucaoMarketplace(id={self.id}, pedido_id={self.pedido_id}, status={self.status})>"
