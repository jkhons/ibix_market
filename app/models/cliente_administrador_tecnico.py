# PDV Ibix - Vínculo Cliente Administrador x Técnicos (Saas.md Fase 6.2)
"""Técnicos vinculados à equipe do Cliente Administrador."""

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class ClienteAdministradorTecnico(BaseModel):
    __tablename__ = "cliente_administrador_tecnicos"

    usuario_id_cliente_admin = Column(
        Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id_tecnico = Column(
        Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )

    cliente_admin = relationship("Usuario", foreign_keys=[usuario_id_cliente_admin])
    tecnico = relationship("Usuario", foreign_keys=[usuario_id_tecnico])

    __table_args__ = (
        Index("idx_cliente_admin_tecnicos_admin_id", "usuario_id_cliente_admin"),
        Index("idx_cliente_admin_tecnicos_tecnico_id", "usuario_id_tecnico"),
        UniqueConstraint(
            "usuario_id_cliente_admin",
            "usuario_id_tecnico",
            name="uq_cliente_admin_tecnico",
        ),
    )
