# PDV Ibix - Schemas para Roles
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RoleBase(BaseModel):
    """Schema base para roles"""
    nome: str = Field(..., min_length=2, max_length=50, description="Nome da role")
    descricao: Optional[str] = Field(None, description="Descrição da role")
    ativo: bool = Field(True, description="Status ativo/inativo")

class RoleCreate(RoleBase):
    """Schema para criação de role"""
    pass

class RoleUpdate(BaseModel):
    """Schema para atualização de role"""
    nome: Optional[str] = Field(None, min_length=2, max_length=50, description="Nome da role")
    descricao: Optional[str] = Field(None, description="Descrição da role")
    ativo: Optional[bool] = Field(None, description="Status ativo/inativo")

class RoleResponse(RoleBase):
    """Schema para resposta de role"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class RoleListResponse(BaseModel):
    """Schema para resposta de lista de roles"""
    roles: List[RoleResponse]
    total: int
    skip: int
    limit: int

