# PDV Ibix - Controle de sincronização (marketplace)
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from ..database.base import BaseModel


class SyncControle(BaseModel):
    """Controle de sincronização estoque/preço por loja."""
    __tablename__ = "sync_controle"

    loja_id = Column(
        Integer,
        ForeignKey("lojas_marketplace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_sync = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, server_default="pendente")
    dados_resumo = Column(Text(), nullable=True)
    log_erros = Column(Text(), nullable=True)
    iniciado_em = Column(DateTime(timezone=True), nullable=True)
    finalizado_em = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<SyncControle(id={self.id}, loja_id={self.loja_id}, tipo_sync='{self.tipo_sync}')>"
