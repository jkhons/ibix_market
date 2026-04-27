# PDV Ibix - Consentimentos LGPD do consumidor
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from ..database.base import Base


class ConsumidorConsentimento(Base):
    __tablename__ = "consumidor_consentimentos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    consumidor_id = Column(Integer, ForeignKey("consumidores_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(30), nullable=False)  # marketing | analytics | terceiros
    aceito = Column(Boolean, nullable=False, server_default="false")
    ip = Column(String(45), nullable=True)

    __table_args__ = (
        UniqueConstraint("consumidor_id", "tipo", name="uq_consumidor_consentimentos_tipo"),
    )

    def __repr__(self):
        return f"<ConsumidorConsentimento(consumidor={self.consumidor_id}, tipo={self.tipo}, aceito={self.aceito})>"
