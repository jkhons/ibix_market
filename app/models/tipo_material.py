# PDV Ibix - Modelo Tipo de Material (estoque)
from sqlalchemy import Boolean, Column, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class TipoMaterial(BaseModel):
    """Tipo de material para classificação de produtos no estoque."""
    __tablename__ = "tipo_material"

    codigo = Column(String(20), nullable=False, unique=True, index=True)
    nome = Column(String(100), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True)

    produtos_cliente = relationship("ProdutoCliente", back_populates="tipo_material_rel")

    def __repr__(self):
        return f"<TipoMaterial(id={self.id}, codigo='{self.codigo}', nome='{self.nome}')>"
