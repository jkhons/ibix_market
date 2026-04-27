# PDV Ibix - Vínculo Administrador x Cliente Administrador (Saas.md)
"""Cliente Administrador vinculado a um Administrador específico."""

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class AdministradorClienteAdministrador(BaseModel):
    __tablename__ = "administrador_cliente_administradores"

    usuario_id_administrador = Column(
        Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id_cliente_administrador = Column(
        Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )

    administrador = relationship("Usuario", foreign_keys=[usuario_id_administrador])
    cliente_administrador = relationship("Usuario", foreign_keys=[usuario_id_cliente_administrador])

    __table_args__ = (
        UniqueConstraint(
            "usuario_id_cliente_administrador",
            name="uq_administrador_cliente_administradores_cliente_admin",
        ),
        Index("idx_admin_cliente_admin_administrador", "usuario_id_administrador"),
        Index("idx_admin_cliente_admin_cliente_admin", "usuario_id_cliente_administrador"),
    )
