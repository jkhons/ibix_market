# PDV Ibix - Payment Provider Config (Fase 3.3 + Marketplace)
"""Configuração de provedor de pagamento por estabelecimento (cliente_id). Conexão OAuth/conexão delegada."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class PaymentProviderConfig(BaseModel):
    """Config do provedor por estabelecimento: provider_code, credenciais, conexão (OAuth), webhook_secret."""
    __tablename__ = "payment_provider_configs"

    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Estabelecimento (clientes.id)",
    )
    provider_code = Column(String(50), nullable=False, comment="pagbank, cielo, stone, efi, mercadopago")
    credentials_encrypted = Column(Text, nullable=True, comment="Credenciais criptografadas (JSON)")
    account_external_id = Column(String(200), nullable=True, comment="ID da conta no provedor (OAuth)")
    webhook_secret_encrypted = Column(Text, nullable=True)
    public_key_encrypted = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    connection_status = Column(String(30), nullable=True, server_default="pending")
    last_validated_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    fee_configs = Column(Text, nullable=True, comment="JSON: taxas por método")
    routing_rules = Column(Text, nullable=True, comment="JSON: prioridade, métodos habilitados")
    is_active = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)
    test_mode = Column(Boolean, nullable=False, default=False)

    cliente = relationship("Cliente", foreign_keys=[cliente_id])

    def __repr__(self):
        return f"<PaymentProviderConfig(id={self.id}, cliente_id={self.cliente_id}, provider_code='{self.provider_code}')>"
