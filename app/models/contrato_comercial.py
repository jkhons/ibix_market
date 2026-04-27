# PDV Ibix - Contrato comercial SaaS (Fase 2)
"""Contrato de assinatura do tenant: vigência, qtd de PDVs contratados, valor mensal."""
from sqlalchemy import Column, Date, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class ContratoComercial(BaseModel):
    """Contrato de assinatura SaaS por tenant."""
    __tablename__ = "contrato_comercial"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    vigencia_inicio = Column(Date, nullable=False)
    vigencia_fim = Column(Date, nullable=True, comment="Null = indeterminado")
    qtd_pdvs_contratados = Column(Integer, nullable=False, default=1)
    valor_mensal_centavos = Column(Integer, nullable=False, comment="Valor total mensal em centavos")
    status = Column(String(20), nullable=False, default="ativo", comment="ativo, encerrado, cancelado")

    tenant = relationship("Tenant", backref="contratos_comerciais")
    aditivos = relationship("ContratoAditivo", back_populates="contrato", cascade="all, delete-orphan", order_by="ContratoAditivo.data_aditivo.desc()")

    __table_args__ = (
        Index("ix_contrato_comercial_tenant_status", "tenant_id", "status"),
        {"comment": "Contrato de assinatura SaaS por tenant"},
    )

    def __repr__(self):
        return f"<ContratoComercial(id={self.id}, tenant_id={self.tenant_id}, pdvs={self.qtd_pdvs_contratados})>"
