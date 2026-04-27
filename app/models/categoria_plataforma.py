# PDV Ibix - Categorias globais da vitrine (marketplace)
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class CategoriaPlataforma(BaseModel):
    """Categorias globais da vitrine (diferente de material_categoria)."""
    __tablename__ = "categorias_plataforma"

    nome = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=True, unique=True)
    descricao = Column(Text(), nullable=True)
    icone = Column(String(50), nullable=True)
    ordem = Column(Integer, nullable=True)
    ativa = Column(Boolean, nullable=False, server_default="true")
    categoria_pai_id = Column(
        Integer,
        ForeignKey("categorias_plataforma.id", ondelete="SET NULL"),
        nullable=True,
    )

    categoria_pai = relationship("CategoriaPlataforma", remote_side="CategoriaPlataforma.id")
    anuncios = relationship("AnuncioPlataforma", back_populates="categoria")

    def __repr__(self):
        return f"<CategoriaPlataforma(id={self.id}, nome='{self.nome}')>"
