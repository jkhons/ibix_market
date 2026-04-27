import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.sql import func

from ..database.base import BaseModel


class TipoContratoEnum(str, enum.Enum):
    """Tipos de contrato disponíveis"""
    calibracao = "calibracao"
    afericao = "afericao"
    manutencao = "manutencao"
    inspecao = "inspecao"
    outros = "outros"


class TemplateContrato(BaseModel):
    """
    Model para templates de contratos reutilizáveis
    Permite criar modelos com variáveis substituíveis
    """
    __tablename__ = "templates_contratos"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(200), nullable=False, comment="Nome do template")
    descricao = Column(Text, nullable=True, comment="Descrição do template")
    conteudo = Column(Text, nullable=False, comment="Conteúdo com variáveis [VARIAVEL]")
    tipo_contrato = Column(
        Enum(TipoContratoEnum),
        nullable=False,
        default=TipoContratoEnum.calibracao,
        comment="Tipo de contrato"
    )
    ativo = Column(Boolean, default=True, nullable=False, comment="Se está ativo para uso")
    
    created_by = Column(Integer, nullable=True, comment="ID do usuário criador")
    updated_by = Column(Integer, nullable=True, comment="ID do usuário que atualizou")
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<TemplateContrato {self.nome} ({self.tipo_contrato})>"

