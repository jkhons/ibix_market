# PDV Ibix - Schemas RevisaoDirecao
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class RevisaoDirecaoBase(BaseModel):
    cliente_id: Optional[int] = None
    data_revisao: date
    participantes: Optional[str] = None
    itens_analisados: Optional[str] = None
    decisoes: Optional[str] = None
    proximas_revisoes: Optional[str] = None


class RevisaoDirecaoCreate(RevisaoDirecaoBase):
    pass


class RevisaoDirecaoUpdate(BaseModel):
    cliente_id: Optional[int] = None
    data_revisao: Optional[date] = None
    participantes: Optional[str] = None
    itens_analisados: Optional[str] = None
    decisoes: Optional[str] = None
    proximas_revisoes: Optional[str] = None


class RevisaoDirecaoResponse(RevisaoDirecaoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
