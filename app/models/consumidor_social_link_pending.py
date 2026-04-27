from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from ..database.base import BaseModel


class ConsumidorSocialLinkPending(BaseModel):
    __tablename__ = "consumidor_social_link_pending"

    consumidor_id = Column(Integer, nullable=False, index=True)
    provider = Column(String(20), nullable=False, index=True)
    provider_user_id = Column(String(255), nullable=False)
    email_provider = Column(String(255), nullable=True)
    email_verified = Column(Boolean, nullable=False, server_default="false")
    nome_provider = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(Text, nullable=True)
