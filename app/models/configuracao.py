# PDV Ibix - Configuração Model
from sqlalchemy import Column, String, Text

from ..database.base import BaseModel


class Configuracao(BaseModel):
    """Modelo para tabela de configurações do sistema"""
    __tablename__ = "configuracoes"
    
    # Campos
    chave = Column(String(100), nullable=False, unique=True)
    valor = Column(Text, nullable=False)
    descricao = Column(String(255))
    
    def __repr__(self):
        return f"<Configuracao(chave='{self.chave}', valor='{self.valor}')>" 