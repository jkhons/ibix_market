# PDV Ibix - Schemas Abertura de Caixa (turno)
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AberturaCaixaAbrir(BaseModel):
    """Payload para abrir caixa (iniciar turno)."""
    caixa_id: int
    valor_inicial: Optional[Decimal] = 0


class AberturaCaixaFechar(BaseModel):
    """Payload para fechar caixa (encerrar turno)."""
    valor_final: Decimal


class AberturaCaixaResponse(BaseModel):
    """Resposta de abertura/turno de caixa."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    caixa_id: int
    usuario_id: Optional[int] = None
    data_abertura: datetime
    data_fechamento: Optional[datetime] = None
    valor_inicial: Decimal
    valor_final: Optional[Decimal] = None
    status: str
    created_at: datetime
    updated_at: datetime
