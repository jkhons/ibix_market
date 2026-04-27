from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class ConsumidorSocialIdentity(BaseModel):
    __tablename__ = "consumidor_social_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_consumidor_social_provider_user"),
        UniqueConstraint("consumidor_id", "provider", name="uq_consumidor_social_consumidor_provider"),
    )

    consumidor_id = Column(Integer, ForeignKey("consumidores_marketplace.id"), nullable=False, index=True)
    provider = Column(String(20), nullable=False, index=True)  # google | facebook | apple
    provider_user_id = Column(String(255), nullable=False, index=True)
    email_provider = Column(String(255), nullable=True)
    email_verified = Column(Boolean, nullable=False, server_default="false")
    nome_provider = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    consumidor = relationship("ConsumidorMarketplace")
