from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class LojaSlugHistory(BaseModel):
    __tablename__ = "loja_slug_history"
    __table_args__ = (
        UniqueConstraint("slug_antigo", name="uq_loja_slug_history_slug_antigo"),
    )

    loja_id = Column(Integer, ForeignKey("lojas_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    slug_antigo = Column(String(100), nullable=False, index=True)

    loja = relationship("LojaMarketplace")
