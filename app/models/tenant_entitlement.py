# PDV Ibix - TenantEntitlement Model (SaaS)
from typing import TYPE_CHECKING

from sqlalchemy import Column, Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class TenantEntitlement(BaseModel):
    """Entitlement: qual módulo está liberado para um tenant (status e limites)."""
    __tablename__ = "tenant_entitlements"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="ativo")  # ativo, suspenso, cancelado
    limits = Column(String(500), nullable=True)  # JSON: ex. {"max_equipamentos": 100}
    vigencia_inicio = Column(Date, nullable=True)
    vigencia_fim = Column(Date, nullable=True)

    tenant = relationship("Tenant", back_populates="entitlements")
    module = relationship("Module", back_populates="entitlements")

    __table_args__ = (
        UniqueConstraint("tenant_id", "module_id", name="uq_tenant_entitlements_tenant_module"),
        Index("ix_tenant_entitlements_tenant_status", "tenant_id", "status"),
        {"comment": "Entitlements: módulos liberados por tenant"},
    )

    def __repr__(self):
        return f"<TenantEntitlement(tenant_id={self.tenant_id}, module_id={self.module_id}, status='{self.status}')>"
