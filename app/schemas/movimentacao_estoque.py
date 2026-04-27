# PDV Ibix - Schemas Movimentação de Estoque (Fase 2)
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MovimentacaoEstoqueCreate(BaseModel):
    """Registrar entrada, saída ou ajuste e atualizar quantidade_atual do produto_cliente."""
    produto_cliente_id: int
    tipo: str = Field(..., description="entrada | saida | ajuste")
    quantidade: Decimal = Field(..., gt=0, description="Quantidade (sempre positiva)")
    valor_unitario: Optional[Decimal] = None
    documento_ref: Optional[str] = None
    observacao: Optional[str] = None


class MovimentacaoEstoqueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    produto_cliente_id: int
    tipo: str
    quantidade: Decimal
    valor_unitario: Optional[Decimal] = None
    documento_ref: Optional[str] = None
    observacao: Optional[str] = None
    usuario_id: Optional[int] = None
    created_at: datetime
