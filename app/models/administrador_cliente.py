# PDV Ibix - Vínculo Administrador x Clientes (Saas.md Fase 3)
"""Administrador só acessa os clientes vinculados nesta tabela."""

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class AdministradorCliente(BaseModel):
    __tablename__ = "administrador_clientes"

    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)

    usuario = relationship("Usuario", foreign_keys=[usuario_id])
    cliente = relationship("Cliente", foreign_keys=[cliente_id])

    __table_args__ = (
        Index("idx_administrador_clientes_usuario_id", "usuario_id"),
        Index("idx_administrador_clientes_cliente_id", "cliente_id"),
    )
