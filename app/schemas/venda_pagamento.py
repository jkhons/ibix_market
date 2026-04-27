# PDV Ibix - Schemas Venda Pagamento (Fase 3.2 - fracionamento)
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class VendaPagamentoBase(BaseModel):
    forma: str  # dinheiro, cartao_credito, cartao_debito, pix, boleto, transferencia, vale, crediario
    valor: Decimal
    status: Optional[str] = "confirmado"
    id_externo: Optional[str] = None
    observacao: Optional[str] = None


class VendaPagamentoCreate(VendaPagamentoBase):
    venda_id: int


class VendaPagamentoResponse(VendaPagamentoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    venda_id: int
    created_at: datetime
    updated_at: datetime
