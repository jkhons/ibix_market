# PDV Ibix - Sessão de checkout marketplace (N pedidos / 1 pagamento)
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class MarketplaceCheckoutSession(BaseModel):
    """Agrupa vários pedidos marketplace cobrados em uma única transação no gateway (modo plataforma)."""

    __tablename__ = "marketplace_checkout_sessions"

    uuid = Column(String(36), nullable=False, unique=True, index=True)
    idempotency_key = Column(String(128), nullable=True, index=True)
    status = Column(String(30), nullable=False, server_default="pendente")
    total_agregado = Column(Numeric(12, 2), nullable=False, server_default="0")

    session_pedidos = relationship(
        "MarketplaceCheckoutSessionPedido",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    transactions = relationship("PaymentTransaction", back_populates="checkout_session")


class MarketplaceCheckoutSessionPedido(BaseModel):
    """Junção sessão ↔ pedido (ordem de exibição)."""

    __tablename__ = "marketplace_checkout_session_pedidos"
    __table_args__ = (UniqueConstraint("session_id", "pedido_id", name="uq_session_pedido"),)

    session_id = Column(Integer, ForeignKey("marketplace_checkout_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    sort_order = Column(Integer, nullable=False, server_default="0")

    session = relationship("MarketplaceCheckoutSession", back_populates="session_pedidos")
    pedido = relationship("PedidoMarketplace", foreign_keys=[pedido_id])
