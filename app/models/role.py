# PDV Ibix - Modelo Role
from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class Role(BaseModel):
    """Modelo para tabela roles (grupos de usuários)"""
    __tablename__ = "roles"
    
    # Colunas
    nome = Column(String(50), nullable=False, unique=True)
    descricao = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True)
    
    # Relacionamentos
    usuarios = relationship("Usuario", back_populates="role")
    role_permissoes = relationship("RolePermissao", back_populates="role", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        {"comment": "Tabela para grupos de usuários (roles) do sistema RBAC"}
    )
    
    def __repr__(self):
        return f"<Role(id={self.id}, nome='{self.nome}', ativo={self.ativo})>" 