# PDV Ibix - Schemas Estabelecimento Fiscal (Fase 3.1.1)
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class EstabelecimentoFiscalBase(BaseModel):
    cliente_id: int
    cnpj: str
    ie: Optional[str] = None
    crt: Optional[int] = None
    certificado_digital_path: Optional[str] = None
    regime_tributario: Optional[str] = None
    serie_nfe: Optional[str] = "1"
    aliquotas_uf: Optional[Any] = None  # JSON
    ativo: bool = True


class EstabelecimentoFiscalCreate(EstabelecimentoFiscalBase):
    pass


class EstabelecimentoFiscalUpdate(BaseModel):
    ie: Optional[str] = None
    crt: Optional[int] = None
    certificado_digital_path: Optional[str] = None
    regime_tributario: Optional[str] = None
    serie_nfe: Optional[str] = None
    aliquotas_uf: Optional[Any] = None
    ativo: Optional[bool] = None


class EstabelecimentoFiscalResponse(EstabelecimentoFiscalBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
