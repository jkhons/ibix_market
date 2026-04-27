# PDV Ibix - Modelo Assinatura
from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class Assinatura(BaseModel):
    """Modelo para tabela assinaturas"""
    __tablename__ = "assinaturas"
    
    # Colunas que existem na tabela atual
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(Enum('inspecao', 'aprovacao', name='tipo_assinatura_enum'), nullable=False)
    autenticacao_rsa = Column(String(255), nullable=True)
    imagem_assinatura = Column(String(255), nullable=True)
    
    # Relacionamentos
    usuario = relationship("Usuario", back_populates="assinaturas")
    
    # Índices
    __table_args__ = (
        {"comment": "Tabela para armazenar assinaturas digitais e manuais dos certificados"}
    ) 