# PDV Ibix - Push token para notificações mobile (FCM)
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from ..database.base import BaseModel


class ConsumidorPushToken(BaseModel):
    __tablename__ = "consumidor_push_tokens"

    consumidor_id = Column(Integer, ForeignKey("consumidores_marketplace.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(512), nullable=False, unique=True)
    plataforma = Column(String(10), nullable=False)  # ios | android
    device_id = Column(String(255), nullable=True)
    ativo = Column(Boolean, nullable=False, server_default="true")

    def __repr__(self):
        return f"<ConsumidorPushToken(id={self.id}, consumidor_id={self.consumidor_id}, plataforma={self.plataforma})>"
