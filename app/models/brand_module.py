# PDV Ibix - brand_modules (módulos ofertados por marca)
from sqlalchemy import Column, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class BrandModule(BaseModel):
    """Junção marca ↔ módulo (catálogo ofertável por produto white-label)."""

    __tablename__ = "brand_modules"

    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)

    brand = relationship("Brand", backref="brand_module_links")
    module = relationship("Module", backref="brand_module_links")

    __table_args__ = (
        UniqueConstraint("brand_id", "module_id", name="uq_brand_modules_brand_module"),
        Index("ix_brand_modules_brand_id", "brand_id"),
        {"comment": "Módulos disponíveis por marca (Ibix: core+marketplace; Solumática: core)"},
    )

    def __repr__(self):
        return f"<BrandModule(brand_id={self.brand_id}, module_id={self.module_id})>"
