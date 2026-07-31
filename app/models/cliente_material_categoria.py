# PDV Ibix — Categorias da vitrine selecionadas pelo lojista (CA) no cadastro
from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class ClienteMaterialCategoria(BaseModel):
    """Vínculo N:N entre cliente (empresa fiscal / CA) e categorias exibidas na vitrine (material_categoria)."""

    __tablename__ = "cliente_material_categorias"

    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True)
    material_categoria_id = Column(
        Integer,
        ForeignKey("material_categoria.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    cliente = relationship("Cliente", back_populates="categorias_vitrine")
    material_categoria = relationship("MaterialCategoria")

    __table_args__ = (
        UniqueConstraint(
            "cliente_id",
            "material_categoria_id",
            name="uq_cliente_material_categoria",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ClienteMaterialCategoria(cliente_id={self.cliente_id}, "
            f"material_categoria_id={self.material_categoria_id})>"
        )
