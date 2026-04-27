# PDV Ibix - Refresh token para renovação segura de JWT do consumidor
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from ..database.base import Base


class ConsumidorRefreshToken(Base):
    """Refresh tokens — created_at manual (sem updated_at, imutável)."""
    __tablename__ = "consumidor_refresh_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    consumidor_id = Column(Integer, ForeignKey("consumidores_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(128), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, server_default="false")
    device_info = Column(String(500), nullable=True)

    def __repr__(self):
        return f"<ConsumidorRefreshToken(id={self.id}, consumidor_id={self.consumidor_id}, revoked={self.revoked})>"
