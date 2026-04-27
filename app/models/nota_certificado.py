# PDV Ibix - Modelo NotaCertificado
from sqlalchemy import Column, Integer, String, Text

from ..database.base import BaseModel


class NotaCertificado(BaseModel):
    """Modelo para tabela notas_certificados"""
    __tablename__ = "notas_certificados"
    
    # Colunas
    tipo_nota = Column(String(50), nullable=False)  # observacao, restricao, aviso
    conteudo = Column(Text, nullable=False)
    prioridade = Column(String(20), default="normal")  # baixa, normal, alta, critica
    ativo = Column(Integer, default=1)  # 1=ativo, 0=inativo
    
    # Relacionamentos (certificado removido - módulo obsoleto)
    
    # Índices
    __table_args__ = (
        {"comment": "Tabela para armazenar notas, observações e restrições dos certificados"}
    ) 