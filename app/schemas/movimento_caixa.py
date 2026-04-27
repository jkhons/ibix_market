# PDV Ibix - Schemas Movimento de Caixa (Fase 3.2 - sangria/suprimento)
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MovimentoCaixaBase(BaseModel):
    tipo: str  # sangria, suprimento
    valor: Decimal
    observacao: Optional[str] = None


class MovimentoCaixaCreate(MovimentoCaixaBase):
    abertura_caixa_id: int
    senha_mestra: Optional[str] = None  # Obrigatório quando o estabelecimento exige senha mestra para sangria/suprimento


class MovimentoCaixaResponse(MovimentoCaixaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    abertura_caixa_id: int
    usuario_id: Optional[int] = None
    created_at: datetime
