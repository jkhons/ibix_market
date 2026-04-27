# PDV Ibix - Tipo de Ordem de Serviço (por tenant CA)
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.base import BaseModel


class OrdemServicoTipo(BaseModel):
    """Tipo de ordem de serviço, escopado por tenant (CA). Nomes podem repetir entre tenants."""
    __tablename__ = "ordem_servico_tipo"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    codigo = Column(String(50), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)

    tenant = relationship("Tenant", backref="ordem_servico_tipos", foreign_keys=[tenant_id])

    __table_args__ = (
        UniqueConstraint("tenant_id", "nome", name="uq_ordem_servico_tipo_tenant_nome"),
        Index("ix_ordem_servico_tipo_tenant_ativo", "tenant_id", "ativo"),
        {"comment": "Tipos de ordem de serviço por tenant (CA); nomes únicos por tenant"},
    )

    def __repr__(self) -> str:
        return f"<OrdemServicoTipo(id={self.id}, tenant_id={self.tenant_id}, nome='{self.nome}')>"
