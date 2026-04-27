# PDV Ibix - Schemas de contrato comercial e aditivo (Fase 2)
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ContratoComercialCreate(BaseModel):
    tenant_id: int
    vigencia_inicio: date
    vigencia_fim: Optional[date] = None
    qtd_pdvs_contratados: int = Field(ge=1, default=1)


class ContratoComercialResponse(BaseModel):
    id: int
    tenant_id: int
    vigencia_inicio: date
    vigencia_fim: Optional[date] = None
    qtd_pdvs_contratados: int
    valor_mensal_centavos: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ContratoAditivoCreate(BaseModel):
    qtd_pdvs_nova: int = Field(ge=1)
    motivo: Optional[str] = None


class ContratoAditivoResponse(BaseModel):
    id: int
    contrato_id: int
    data_aditivo: date
    qtd_pdvs_anterior: int
    qtd_pdvs_nova: int
    valor_anterior_centavos: int
    valor_novo_centavos: int
    motivo: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MeusLimitesResponse(BaseModel):
    max_pdvs: int
    pdvs_usados: int
    pdvs_disponiveis: int
    valor_mensal_centavos: int
    valor_exibicao: str
    pode_criar_pdv: bool
