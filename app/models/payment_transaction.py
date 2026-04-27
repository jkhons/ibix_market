# PDV Ibix - Payment Transaction (Fase 3.3 + Marketplace)
"""Transação unificada de pagamento (gateway-agnóstica). PDV: venda_id/caixa_id. Marketplace: pedido_id (tentativa por pedido)."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class PaymentTransaction(BaseModel):
    """Transação: uuid, estabelecimento, venda/pdv (PDV) ou pedido (marketplace), provedor, método, valor, status."""
    __tablename__ = "payment_transactions"

    uuid = Column(String(36), nullable=False, unique=True, index=True, comment="UUID público")
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True)
    venda_id = Column(Integer, ForeignKey("vendas.id", ondelete="SET NULL"), nullable=True, index=True)
    caixa_id = Column(Integer, ForeignKey("caixas.id", ondelete="SET NULL"), nullable=True)
    pedido_id = Column(Integer, ForeignKey("pedidos_marketplace.id", ondelete="SET NULL"), nullable=True, index=True)
    checkout_session_id = Column(
        Integer,
        ForeignKey("marketplace_checkout_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Checkout unificado: um pagamento para vários pedidos marketplace",
    )
    provider_code = Column(String(50), nullable=True)
    provider_transaction_id = Column(String(100), nullable=True)
    provider_checkout_id = Column(String(200), nullable=True, comment="ID do checkout no provedor")
    provider_status = Column(String(50), nullable=True, comment="Status bruto do provedor")
    provider_response = Column(Text, nullable=True, comment="JSON auditoria")
    payment_method = Column(
        String(30),
        nullable=False,
        comment="credit, debit, pix, boleto, cash, transfer",
    )
    payment_submethod = Column(String(50), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    installments = Column(Integer, nullable=True, default=1)
    status = Column(
        String(30),
        nullable=False,
        comment="pending, processing, authorized, paid, failed, refunded, cancelled",
    )
    status_history = Column(Text, nullable=True, comment="JSON")
    attempt_number = Column(Integer, nullable=True, default=1, comment="Número da tentativa no pedido")
    is_active = Column(Boolean, nullable=True, default=True, comment="Tentativa vigente (apenas uma True por pedido)")
    authorized_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    reconciliation_status = Column(
        String(20),
        nullable=True,
        default="pending",
        comment="pending, matched, divergence",
    )
    reconciliation_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data em que a transação foi conciliada com extrato do provedor",
    )
    modo_recebimento = Column(
        String(20), nullable=True,
        comment="'direto' = CA recebeu; 'plataforma' = plataforma recebeu (para repasse)",
    )
    repasse_status_id = Column(
        Integer,
        ForeignKey("status_repasse.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Status de repasse (só para modo_recebimento=plataforma)",
    )

    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    repasse_status = relationship("RepasseStatus", foreign_keys=[repasse_status_id])
    venda = relationship("Venda", foreign_keys=[venda_id])
    caixa = relationship("Caixa", foreign_keys=[caixa_id])
    pedido = relationship("PedidoMarketplace", foreign_keys=[pedido_id])
    checkout_session = relationship("MarketplaceCheckoutSession", foreign_keys=[checkout_session_id], back_populates="transactions")
    splits = relationship("TransactionSplit", back_populates="transaction", cascade="all, delete-orphan")
    logs = relationship("PaymentLog", back_populates="transaction", cascade="all, delete-orphan")
    refunds = relationship("Refund", back_populates="payment_transaction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PaymentTransaction(id={self.id}, uuid='{self.uuid}', status='{self.status}')>"
