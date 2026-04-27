# PDV Ibix - TipoEquipamento Schemas
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TipoEquipamentoBase(BaseModel):
    tipo_equipamento: str
    inf_adicionais: Optional[str] = None

class TipoEquipamentoCreate(TipoEquipamentoBase):
    pass

class TipoEquipamentoUpdate(BaseModel):
    tipo_equipamento: Optional[str] = None
    inf_adicionais: Optional[str] = None

class TipoEquipamentoResponse(TipoEquipamentoBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

