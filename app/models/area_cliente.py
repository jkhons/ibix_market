# PDV Ibix - Modelo AreaCliente
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass

class AreaCliente(BaseModel):
    """Modelo para tabela areas_cliente"""
    __tablename__ = "areas_cliente"
    
    # Colunas
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    nome_area = Column(String(100), nullable=False)  # administrador, tecnico, visualizador
    permissoes = Column(Text, nullable=True)  # JSON com permissões específicas
    data_acesso = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ultimo_acesso = Column(DateTime(timezone=True), nullable=True)
    ip_acesso = Column(String(45), nullable=True)
    ativo = Column(Boolean, default=True)
    token_acesso = Column(String(255), nullable=True)
    data_expiracao_token = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    cliente = relationship("Cliente", back_populates="areas_cliente")
    usuario = relationship("Usuario", back_populates="areas_cliente")
    downloads_cliente = relationship("DownloadCliente", back_populates="area_cliente", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        {"comment": "Tabela para controle de acesso dos clientes à área restrita"}
    ) 