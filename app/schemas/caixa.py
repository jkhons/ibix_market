# PDV Ibix - Schemas Caixa (cadastro por empresa fiscal)
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CaixaCreate(BaseModel):
    identificador: str = Field(..., min_length=1, max_length=80, description="Nome do caixa")
    ativo: bool = True


class CaixaUpdate(BaseModel):
    identificador: Optional[str] = Field(None, min_length=1, max_length=80)
    ativo: Optional[bool] = None


class CaixaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    cliente_id: Optional[int] = Field(None, description="Estabelecimento (cliente) vinculado à empresa fiscal do caixa")
    identificador: str
    ativo: bool
    created_at: datetime
    updated_at: datetime
