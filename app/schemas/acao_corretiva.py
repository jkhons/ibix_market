# PDV Ibix - Schemas AcaoCorretiva
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class AcaoCorretivaBase(BaseModel):
    processo_id: int
    nc_numero: Optional[str] = None
    causa_raiz: Optional[str] = None
    acao_planejada: str
    responsavel_id: Optional[int] = None
    data_prevista: Optional[date] = None
    data_conclusao: Optional[date] = None
    eficacia_verificada: Optional[bool] = None
    observacoes: Optional[str] = None


class AcaoCorretivaCreate(AcaoCorretivaBase):
    pass


class AcaoCorretivaUpdate(BaseModel):
    nc_numero: Optional[str] = None
    causa_raiz: Optional[str] = None
    acao_planejada: Optional[str] = None
    responsavel_id: Optional[int] = None
    data_prevista: Optional[date] = None
    data_conclusao: Optional[date] = None
    eficacia_verificada: Optional[bool] = None
    observacoes: Optional[str] = None


class AcaoCorretivaResponse(AcaoCorretivaBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
