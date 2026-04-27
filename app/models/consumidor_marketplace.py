# PDV Ibix - Consumidor Marketplace (cliente final que compra na loja)
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class ConsumidorMarketplace(BaseModel):
    """Cadastro do cliente consumidor / cliente final (quem compra na vitrine)."""
    __tablename__ = "consumidores_marketplace"

    tenant_id = Column(Integer, nullable=True, index=True)  # clientes.id; NULL só para órfãos (backfill)
    email = Column(String(255), nullable=False)
    senha_hash = Column(String(255), nullable=True)  # NULL para GUEST até completar cadastro
    nome = Column(String(200), nullable=False)
    telefone = Column(String(20), nullable=True)
    documento = Column(String(20), nullable=True)
    aceite_termos = Column(Boolean, nullable=False, server_default="false")
    ativo = Column(Boolean, nullable=False, server_default="true")
    tipo_pessoa = Column(String(2), nullable=True)
    tipo_consumidor = Column(String(20), nullable=False, server_default="REGISTERED", index=True)
    status_cadastro = Column(String(20), nullable=False, server_default="COMPLETO", index=True)
    aceite_marketing = Column(Boolean, nullable=False, server_default="false")
    aceite_marketing_em = Column(DateTime(timezone=True), nullable=True)
    origem_cadastro = Column(String(50), nullable=True)
    canal_origem = Column(String(50), nullable=True)
    origem_social_provider = Column(String(20), nullable=True)
    email_verificado = Column(Boolean, nullable=False, server_default="false")
    avatar_url = Column(String(500), nullable=True)
    utm_source = Column(String(150), nullable=True)
    utm_medium = Column(String(150), nullable=True)
    utm_campaign = Column(String(150), nullable=True)
    primeira_compra_em = Column(DateTime(timezone=True), nullable=True)
    ultima_compra_em = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # UNIQUE(tenant_id, LOWER(email)) WHERE deleted_at IS NULL está na migration (índice parcial)

    enderecos = relationship("EnderecoConsumidor", back_populates="consumidor", cascade="all, delete-orphan")
    pedidos = relationship("PedidoMarketplace", back_populates="comprador")

    def __repr__(self):
        return f"<ConsumidorMarketplace(id={self.id}, email='{self.email}', tipo={self.tipo_consumidor})>"
