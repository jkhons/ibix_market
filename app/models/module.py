# PDV Ibix - Module Model (SaaS)
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Index, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class Module(BaseModel):
    """Catálogo de módulos do sistema (ex.: certificados, fiscal, qualidade)."""
    __tablename__ = "modules"

    nome = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    descricao = Column(String(500), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)

    entitlements = relationship("TenantEntitlement", back_populates="module", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_modules_ativo", "ativo"),
        {"comment": "Catálogo de módulos SaaS"},
    )

    def __repr__(self):
        return f"<Module(id={self.id}, nome='{self.nome}', slug='{self.slug}')>"
