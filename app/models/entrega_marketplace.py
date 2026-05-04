# PDV Ibix - Entrega marketplace (logística local)
# Entidade própria; pedido continua comercial. 1 entrega por pedido no MVP.
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class EntregaMarketplace(BaseModel):
    """Entrega logística a partir de um pedido marketplace."""
    __tablename__ = "entregas_marketplace"

    pedido_id = Column(Integer, ForeignKey("pedidos_marketplace.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    entregador_id = Column(Integer, ForeignKey("entregadores.id", ondelete="SET NULL"), nullable=True, index=True)

    status = Column(String(30), nullable=False, server_default="aguardando_publicacao", index=True)
    valor_frete = Column(Numeric(12, 2), nullable=False, server_default="0")
    tipo_veiculo_aceito = Column(String(20), nullable=True)  # moto, carro, utilitario, qualquer

    nome_retirada = Column(String(150), nullable=True)
    telefone_retirada = Column(String(30), nullable=True)
    endereco_retirada_json = Column(JSONB, nullable=True)

    nome_destinatario = Column(String(150), nullable=True)
    telefone_destinatario = Column(String(30), nullable=True)
    endereco_entrega_json = Column(JSONB, nullable=True)

    observacoes = Column(Text(), nullable=True)
    aceita_ate_em = Column(DateTime(timezone=True), nullable=True)
    publicada_em = Column(DateTime(timezone=True), nullable=True)
    aceita_em = Column(DateTime(timezone=True), nullable=True)
    retirada_em = Column(DateTime(timezone=True), nullable=True)
    saiu_para_entrega_em = Column(DateTime(timezone=True), nullable=True)
    entregue_em = Column(DateTime(timezone=True), nullable=True)
    cancelada_em = Column(DateTime(timezone=True), nullable=True)
    codigo_confirmacao = Column(String(20), nullable=True)

    status_pagamento_entregador = Column(String(30), nullable=False, server_default="pendente")
    pagamento_entregador_obs = Column(Text(), nullable=True)
    pagamento_entregador_atualizado_em = Column(DateTime(timezone=True), nullable=True)
    pagamento_entregador_atualizado_por_usuario_id = Column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )

    pedido = relationship("PedidoMarketplace", backref="entrega_marketplace", uselist=False)
    entregador = relationship("Entregador", back_populates="entregas", foreign_keys=[entregador_id])
    eventos = relationship("EntregaEvento", back_populates="entrega", cascade="all, delete-orphan", order_by="EntregaEvento.created_at")

    def __repr__(self):
        return f"<EntregaMarketplace(id={self.id}, pedido_id={self.pedido_id}, status='{self.status}')>"
