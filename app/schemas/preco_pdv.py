# PDV Ibix - Schemas de preços PDV (Fase 2)
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class PrecoPdvCreate(BaseModel):
    valor_base_centavos: int = Field(ge=1)
    valor_pdv_adicional_centavos: int = Field(ge=0)
    vigencia_inicio: date


class PrecoPdvUpdate(BaseModel):
    valor_base_centavos: Optional[int] = Field(None, ge=1)
    valor_pdv_adicional_centavos: Optional[int] = Field(None, ge=0)
    ativo: Optional[bool] = None


class PrecoPdvResponse(BaseModel):
    id: int
    valor_base_centavos: int
    valor_pdv_adicional_centavos: int
    vigencia_inicio: date
    ativo: bool
    created_at: datetime

    class Config:
        from_attributes = True
