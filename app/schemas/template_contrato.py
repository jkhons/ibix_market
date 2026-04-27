from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TipoContratoEnum(str, Enum):
    """Tipos de contrato disponíveis"""
    calibracao = "calibracao"
    afericao = "afericao"
    manutencao = "manutencao"
    inspecao = "inspecao"
    outros = "outros"


class TemplateContratoBase(BaseModel):
    """Schema base para template de contrato"""
    nome: str = Field(..., max_length=200, description="Nome do template")
    descricao: Optional[str] = Field(None, description="Descrição do template")
    conteudo: str = Field(..., description="Conteúdo do contrato com variáveis [VARIAVEL]")
    tipo_contrato: TipoContratoEnum = Field(default=TipoContratoEnum.calibracao, description="Tipo de contrato")
    ativo: bool = Field(default=True, description="Se o template está ativo")


class TemplateContratoCreate(TemplateContratoBase):
    """Schema para criar template"""
    pass


class TemplateContratoUpdate(BaseModel):
    """Schema para atualizar template"""
    nome: Optional[str] = Field(None, max_length=200)
    descricao: Optional[str] = None
    conteudo: Optional[str] = None
    tipo_contrato: Optional[TipoContratoEnum] = None
    ativo: Optional[bool] = None


class TemplateContratoResponse(BaseModel):
    """Schema de resposta do template"""
    id: int
    nome: str
    descricao: Optional[str] = None
    conteudo: str
    tipo_contrato: str  # Retorna como string, não enum
    ativo: bool
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        use_enum_values = True


class TemplateContratoList(BaseModel):
    """Schema para lista de templates"""
    templates: list[TemplateContratoResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int

