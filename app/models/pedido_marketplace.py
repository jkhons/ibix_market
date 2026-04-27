# PDV Ibix - Pedido do marketplace (e-commerce)
from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class PedidoMarketplace(BaseModel):
    """Pedido do e-commerce (diferente de pedidos = fluxo interno)."""
    __tablename__ = "pedidos_marketplace"

    tenant_id = Column(Integer, nullable=False, index=True)  # clientes.id
    loja_id = Column(
        Integer,
        ForeignKey("lojas_marketplace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    comprador_id = Column(
        Integer,
        ForeignKey("consumidores_marketplace.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    numero_pedido = Column(String(50), nullable=False, index=True)
    comprador_nome = Column(String(200), nullable=False)
    comprador_email = Column(String(255), nullable=True)
    comprador_telefone = Column(String(20), nullable=True)
    comprador_documento = Column(String(20), nullable=True)
    destinatario_nome = Column(String(200), nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=False)
    desconto = Column(Numeric(10, 2), nullable=False, server_default="0")
    taxa_entrega = Column(Numeric(10, 2), nullable=False, server_default="0")
    total = Column(Numeric(10, 2), nullable=False)
    formato_frete_snapshot = Column(String(20), nullable=True)
    custo_frete = Column(Numeric(10, 2), nullable=True)
    lucro_frete = Column(Numeric(10, 2), nullable=True)
    comissao_plataforma = Column(Numeric(10, 2), nullable=True)
    percentual_comissao = Column(Numeric(5, 2), nullable=True)
    valor_liquido_loja = Column(Numeric(10, 2), nullable=True)
    status_pedido = Column(String(30), nullable=False, server_default="aguardando_pagamento")
    status_pagamento = Column(String(30), nullable=False, server_default="pendente")
    status_entrega = Column(String(30), nullable=False, server_default="pendente")
    endereco_entrega = Column(Text(), nullable=True)
    tipo_entrega = Column(String(20), nullable=False)
    gateway_pagamento = Column(String(50), nullable=True)
    transaction_id = Column(String(200), nullable=True)
    split_info = Column(Text(), nullable=True)
    origem_pedido = Column(String(30), nullable=False, server_default="checkout_guest")
    aceite_marketing_snapshot = Column(Boolean, nullable=False, server_default="false")
    aceite_politica_privacidade_snapshot = Column(Boolean, nullable=False, server_default="true")
    canal_origem = Column(String(50), nullable=True)
    utm_source = Column(String(100), nullable=True)
    utm_medium = Column(String(100), nullable=True)
    utm_campaign = Column(String(150), nullable=True)
    observacoes_cliente = Column(Text(), nullable=True)
    idempotency_key = Column(String(128), nullable=True, index=True, comment="Chave de idempotência do checkout")

    loja = relationship("LojaMarketplace", back_populates="pedidos")
    comprador = relationship("ConsumidorMarketplace", back_populates="pedidos")
    itens = relationship("PedidoItemMarketplace", back_populates="pedido", cascade="all, delete-orphan")
    reservas_estoque = relationship("ReservaEstoqueMarketplace", back_populates="pedido", cascade="all, delete-orphan")
    status_eventos = relationship(
        "PedidoStatusEvento",
        back_populates="pedido",
        cascade="all, delete-orphan",
        order_by="PedidoStatusEvento.created_at",
    )

    def __repr__(self):
        return f"<PedidoMarketplace(id={self.id}, numero_pedido='{self.numero_pedido}', total={self.total})>"
