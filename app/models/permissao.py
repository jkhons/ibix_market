# PDV Ibix - Modelo Permissao
from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class Permissao(BaseModel):
    """Modelo para tabela permissoes (ações do sistema)"""
    __tablename__ = "permissoes"
    
    # Colunas
    nome = Column(String(100), nullable=False, unique=True)
    descricao = Column(Text, nullable=True)
    modulo = Column(String(50), nullable=False)  # usuarios, certificados, clientes, etc.
    acao = Column(String(50), nullable=False)    # criar, editar, excluir, visualizar
    ativo = Column(Boolean, default=True)
    
    # Relacionamentos
    role_permissoes = relationship("RolePermissao", back_populates="permissao", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        {"comment": "Tabela para ações do sistema (permissoes) do sistema RBAC"}
    )
    
    def __repr__(self):
        return f"<Permissao(id={self.id}, nome='{self.nome}', modulo='{self.modulo}', acao='{self.acao}')>" 