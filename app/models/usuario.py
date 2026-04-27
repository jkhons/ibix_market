# PDV Ibix - Usuario Model
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass

class Usuario(BaseModel):
    """Modelo para tabela de usuários"""
    __tablename__ = "usuarios"
    
    # Campos
    nome = Column(String(255), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=False)
    cargo = Column(String(100), nullable=False)
    ativo = Column(Boolean, default=True)
    cpf = Column(String(14), nullable=True, index=True, comment="CPF do usuário (opcional)")
    rg = Column(String(20), nullable=True, comment="RG do usuário (opcional)")
    documento_path = Column(String(500), nullable=True, comment="Caminho do documento/anexo do usuário (opcional)")
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)  # Pode ser NULL inicialmente
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Tenant SaaS: organização do usuário (nullable para compatibilidade)",
    )
    # Contador: vínculo ao Cliente Administrador cujos clientes ele pode ver (notas fiscais/serviço)
    contador_vinculado_cliente_administrador_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        comment="Se role=Contador: usuario_id do Cliente Administrador cujos clientes este contador pode ver",
    )

    # Relacionamentos
    role = relationship("Role", back_populates="usuarios")
    tenant = relationship("Tenant", back_populates="usuarios", foreign_keys=[tenant_id])
    assinaturas = relationship("Assinatura", back_populates="usuario")
    areas_cliente = relationship("AreaCliente", back_populates="usuario")
    ordens_servico_responsavel = relationship(
        "OrdemServico",
        back_populates="responsavel",
        foreign_keys="OrdemServico.responsavel_id",
    )
    
    # Índices
    __table_args__ = (
        Index("idx_usuarios_email", "email"),
        Index("idx_usuarios_ativo", "ativo"),
        Index("idx_usuarios_tenant_id", "tenant_id"),
    )
    
    def __repr__(self):
        return f"<Usuario(id={self.id}, nome='{self.nome}', email='{self.email}')>" 