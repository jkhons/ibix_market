"""
PDV Ibix - Schemas Pydantic para Permissões
Definição de schemas para validação de dados de permissões
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PermissaoBase(BaseModel):
    """Schema base para permissão"""
    nome: str = Field(..., min_length=3, max_length=100, description="Nome da permissão (ex: usuarios:visualizar)")
    descricao: Optional[str] = Field(None, description="Descrição da permissão")
    modulo: str = Field(..., min_length=2, max_length=50, description="Módulo da permissão")
    acao: str = Field(..., min_length=2, max_length=50, description="Ação da permissão")
    ativo: bool = Field(True, description="Status ativo/inativo")


class PermissaoCreate(PermissaoBase):
    """Schema para criação de permissão"""
    pass


class PermissaoUpdate(BaseModel):
    """Schema para atualização de permissão"""
    nome: Optional[str] = Field(None, min_length=3, max_length=100, description="Nome da permissão")
    descricao: Optional[str] = Field(None, description="Descrição da permissão")
    modulo: Optional[str] = Field(None, min_length=2, max_length=50, description="Módulo da permissão")
    acao: Optional[str] = Field(None, min_length=2, max_length=50, description="Ação da permissão")
    ativo: Optional[bool] = Field(None, description="Status ativo/inativo")


class PermissaoResponse(PermissaoBase):
    """Schema para resposta de permissão"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PermissaoListResponse(BaseModel):
    """Schema para listagem de permissões"""
    permissoes: List[PermissaoResponse]
    total: int
    modulos: Dict[str, int]  # Contador de permissões por módulo
    skip: int
    limit: int


class PermissaoSimple(BaseModel):
    """Schema simplificado de permissão (para listagens)"""
    id: int
    nome: str
    modulo: str
    acao: str
    descricao: Optional[str] = None
    
    class Config:
        from_attributes = True


class RolePermissoesResponse(BaseModel):
    """Schema para resposta de permissões de uma role"""
    role_id: int
    role_nome: str
    permissoes: List[PermissaoSimple]
    total_permissoes: int
    permissoes_ids: List[int]


class RolePermissoesUpdate(BaseModel):
    """Schema para atualização de permissões de uma role"""
    permissoes_ids: List[int] = Field(..., description="Lista de IDs das permissões")


class PermissoesPorModuloResponse(BaseModel):
    """Schema para resposta de permissões agrupadas por módulo"""
    modulo: str
    permissoes: List[PermissaoSimple]
    total: int
    total_selecionadas: Optional[int] = 0  # Quantas estão selecionadas na role atual

