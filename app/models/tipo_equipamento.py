# PDV Ibix - Modelo TipoEquipamento
from sqlalchemy import Column, String, Text

from app.database.base import BaseModel


class TipoEquipamento(BaseModel):
    """Modelo para tabela tipo_equipamento"""
    __tablename__ = "tipo_equipamento"
    
    # Colunas
    tipo_equipamento = Column(String(255), nullable=False)
    inf_adicionais = Column(Text, nullable=True)
    
    # Índices
    __table_args__ = (
        {"comment": "Tabela para tipos de equipamentos"}
    )
    
    def __repr__(self):
        return f"<TipoEquipamento(id={self.id}, tipo_equipamento='{self.tipo_equipamento}')>"

