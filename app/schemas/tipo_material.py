# PDV Ibix - Schemas Tipo de Material (estoque)
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TipoMaterialBase(BaseModel):
    codigo: str
    nome: str
    ativo: bool = True


class TipoMaterialCreate(TipoMaterialBase):
    pass


class TipoMaterialUpdate(BaseModel):
    codigo: Optional[str] = None
    nome: Optional[str] = None
    ativo: Optional[bool] = None


class TipoMaterialResponse(TipoMaterialBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
