# PDV Ibix — Regras de taxas marketplace (Super Admin Billing)
from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class MarketplaceTaxaRegra(BaseModel):
    """Regra de taxa plataforma (faixas) + gateway; Geral ou por tenant."""

    __tablename__ = "marketplace_taxa_regras"

    nome = Column(String(200), nullable=False)
    ativo = Column(Boolean, nullable=False, server_default="true")
    escopo = Column(String(20), nullable=False)  # geral | tenant
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    payload = Column(Text(), nullable=False)  # JSON validado em API

    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    __table_args__ = (
        CheckConstraint("escopo IN ('geral', 'tenant')", name="ck_marketplace_taxa_regras_escopo_model"),
        CheckConstraint(
            "(escopo = 'geral' AND tenant_id IS NULL) OR (escopo = 'tenant' AND tenant_id IS NOT NULL)",
            name="ck_marketplace_taxa_regras_escopo_tenant_model",
        ),
        {"comment": "Taxas marketplace: Billing Super Admin"},
    )
