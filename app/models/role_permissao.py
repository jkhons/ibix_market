# PDV Ibix - Modelo RolePermissao
from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class RolePermissao(BaseModel):
    """Modelo para tabela role_permissoes (relação N:N entre roles e permissoes)"""
    __tablename__ = "role_permissoes"
    
    # Colunas
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permissao_id = Column(Integer, ForeignKey("permissoes.id"), nullable=False)
    
    # Relacionamentos
    role = relationship("Role", back_populates="role_permissoes")
    permissao = relationship("Permissao", back_populates="role_permissoes")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('role_id', 'permissao_id', name='unique_role_permissao'),
        {"comment": "Tabela de relacionamento N:N entre roles e permissoes"}
    )
    
    def __repr__(self):
        return f"<RolePermissao(role_id={self.role_id}, permissao_id={self.permissao_id})>" 