# PDV Ibix - Plan Model (SaaS)
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Index, Numeric, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class Plan(BaseModel):
    """Catálogo de planos de assinatura (SaaS)."""
    __tablename__ = "plans"

    nome = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    descricao = Column(String(500), nullable=True)
    preco = Column(Numeric(12, 2), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)

    tenants = relationship("Tenant", back_populates="plan", foreign_keys="Tenant.plan_id")

    __table_args__ = (
        Index("ix_plans_ativo", "ativo"),
        {"comment": "Catálogo de planos SaaS"},
    )

    def __repr__(self):
        return f"<Plan(id={self.id}, nome='{self.nome}', slug='{self.slug}')>"
