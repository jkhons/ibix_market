# PDV Ibix — Notificações in-app do painel web (CA / usuários internos)
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class UsuarioNotificacao(BaseModel):
    """Inbox do usuário no CA (ícone sino). Espelha a tabela criada em produção (nt01)."""

    __tablename__ = "usuario_notificacoes"
    __table_args__ = (
        UniqueConstraint("usuario_id", "tipo", "ref_id", name="uq_usuario_notif_user_tipo_ref"),
    )

    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    tipo = Column(String(60), nullable=False, index=True)
    ref_id = Column(Integer, nullable=True, index=True)
    titulo = Column(String(255), nullable=False)
    mensagem = Column(Text, nullable=False)
    link = Column(Text, nullable=True)
    icone = Column(String(40), nullable=True)
    cor = Column(String(20), nullable=True)
    dados_json = Column(JSONB, nullable=True)
    lida = Column(Boolean, nullable=False, server_default="false", index=True)
    lida_em = Column(DateTime(timezone=True), nullable=True)

    usuario = relationship("Usuario", foreign_keys=[usuario_id])

    def __repr__(self):
        return f"<UsuarioNotificacao(id={self.id}, usuario_id={self.usuario_id}, tipo={self.tipo})>"
