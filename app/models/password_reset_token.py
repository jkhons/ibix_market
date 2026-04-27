# PDV Ibix - Token de redefinição de senha (PDV e Loja)
from sqlalchemy import Column, DateTime, Index, Integer, String

from ..database.base import BaseModel


class PasswordResetToken(BaseModel):
    """Token de uso único para redefinição de senha (Usuario PDV ou ConsumidorMarketplace Loja)."""
    __tablename__ = "password_reset_tokens"

    tipo = Column(String(10), nullable=False, comment="pdv | loja")
    entidade_id = Column(Integer, nullable=False, comment="usuario_id ou consumidor_id")
    token_hash = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_password_reset_tokens_token_hash", "token_hash"),
        Index("ix_password_reset_tokens_tipo_entidade", "tipo", "entidade_id"),
    )
