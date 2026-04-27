# PDV Ibix - Audit log append-only (E4.4 confirmação de impl.)
# Rastreabilidade: quem/onde/quando/o quê. Não atualizar nem deletar registros.
from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.sql import func

from ..database.base import Base  # append-only: sem updated_at (BaseModel tem updated_at)


class AuditLog(Base):
    """Registro de auditoria append-only (event_store / audit_log)."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id = Column(Integer, nullable=True, index=True)
    tenant_id = Column(Integer, nullable=True, index=True, comment="Tenant SaaS (nullable para SuperAdmin)")
    recurso_tipo = Column(String(100), nullable=True, index=True)
    recurso_id = Column(Integer, nullable=True, index=True)
    acao = Column(String(100), nullable=False, index=True)
    ip = Column(String(45), nullable=True)
    request_id = Column(String(64), nullable=True, index=True)
    detalhes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_audit_log_created_at", "created_at"),
        Index("ix_audit_log_user_created", "user_id", "created_at"),
        # tenant_id já tem index=True na coluna
        {"comment": "Audit log append-only (quem/onde/quando/o quê)"},
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, acao='{self.acao}', user_id={self.user_id})>"
