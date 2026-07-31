# PDV Ibix - Schemas regiões de cobertura da plataforma (marketplace)
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PlataformaCidadeCoberturaPublic(BaseModel):
    """Lista pública para vitrine / CA — só ativos."""

    id: int
    cidade: str
    uf: str
    codigo_ibge: Optional[int] = None

    model_config = {"from_attributes": True}


class PlataformaCidadeCoberturaAdmin(BaseModel):
    """Visão administrativa inclui flags."""

    id: int
    cidade: str
    uf: str
    codigo_ibge: Optional[int] = None
    ativo: bool = True
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PlataformaCidadeCoberturaCreate(BaseModel):
    cidade: str = Field(..., min_length=1, max_length=120)
    uf: str = Field(..., min_length=2, max_length=2)
    codigo_ibge: Optional[int] = None


class PlataformaCidadeCoberturaUpdate(BaseModel):
    cidade: Optional[str] = Field(None, min_length=1, max_length=120)
    uf: Optional[str] = Field(None, min_length=2, max_length=2)
    codigo_ibge: Optional[int] = None
    ativo: Optional[bool] = None
