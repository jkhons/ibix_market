# PDV Ibix - Tenant Model (SaaS)
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class Tenant(BaseModel):
    """Tenant (organização/empresa) que assina planos. Multi-tenant SaaS."""
    __tablename__ = "tenants"

    nome = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False, index=True)
    external_id = Column(String(128), nullable=True, unique=True, index=True, comment="ID no gateway de pagamento")
    ativo = Column(Boolean, default=True, nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True)

    default_empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="SET NULL"), nullable=True, index=True, comment="Empresa emissora padrão para NFS-e de subscription")
    ca_cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True, comment="Cliente CA (tomador padrão) para NFS-e de subscription")

    cupom_impressao_modo = Column(String(20), nullable=True, comment="automatico | manual - impressão cupom ao final da venda")
    cupom_tipo = Column(String(20), nullable=True, comment="nao_fiscal | fiscal - tipo de cupom")
    cupom_fiscal_emissor = Column(String(20), nullable=True, comment="interno | externo - futuro, para cupom fiscal")

    google_cse_limite_diario = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Máximo de buscas Google CSE (imagem) por dia; 0 = bloqueado",
    )
    google_cse_uso_dia = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Buscas já consumidas no dia de referência",
    )
    google_cse_uso_data = Column(Date, nullable=True, comment="Data do contador google_cse_uso_dia")

    plan = relationship("Plan", back_populates="tenants", foreign_keys=[plan_id], lazy="select")
    brand = relationship("Brand", foreign_keys=[brand_id])
    default_empresa = relationship("Empresa", foreign_keys=[default_empresa_id])
    ca_cliente = relationship("Cliente", foreign_keys=[ca_cliente_id])
    usuarios = relationship("Usuario", back_populates="tenant", foreign_keys="Usuario.tenant_id")
    entitlements = relationship("TenantEntitlement", back_populates="tenant", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("brand_id", "slug", name="uq_tenants_brand_slug"),
        Index("ix_tenants_ativo", "ativo"),
        {"comment": "Tenant SaaS: organização que assina planos"},
    )

    def __repr__(self):
        return f"<Tenant(id={self.id}, nome='{self.nome}', slug='{self.slug}')>"
