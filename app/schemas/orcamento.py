# PDV Ibix - Schemas de Orçamento
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class OrcamentoItemCreate(BaseModel):
    """Item para criação de orçamento."""
    produto_cliente_id: int = Field(..., description="ID do produto (produtos_cliente)")
    quantidade: float = Field(..., gt=0)
    preco_unitario: float = Field(..., ge=0)
    desconto_percentual: Optional[float] = Field(None, ge=0, le=100)
    desconto_valor: Optional[float] = Field(None, ge=0)
    observacao_item: Optional[str] = None


class OrcamentoItemResponse(BaseModel):
    """Item de orçamento na resposta."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    orcamento_id: int
    produto_cliente_id: int
    codigo_produto: Optional[str] = None
    descricao_produto: Optional[str] = None
    quantidade: Decimal
    preco_unitario: Decimal
    desconto_percentual: Optional[Decimal] = None
    desconto_valor: Optional[Decimal] = None
    total_item: Decimal
    observacao_item: Optional[str] = None


class OrcamentoCreate(BaseModel):
    """Criação de orçamento."""
    cliente_id: int = Field(..., description="Estabelecimento que emite")
    destinatario_id: Optional[int] = None
    data_validade: date = Field(..., description="Data de validade do orçamento")
    observacoes: Optional[str] = None
    condicoes_pagamento: Optional[str] = None
    itens: List[OrcamentoItemCreate] = Field(..., min_length=1)


class OrcamentoUpdate(BaseModel):
    """Atualização parcial de orçamento (rascunho)."""
    destinatario_id: Optional[int] = None
    data_validade: Optional[date] = None
    observacoes: Optional[str] = None
    condicoes_pagamento: Optional[str] = None
    itens: Optional[List[OrcamentoItemCreate]] = None


class OrcamentoResponse(BaseModel):
    """Orçamento na resposta."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    cliente_id: int
    vendedor_id: Optional[int] = None
    destinatario_id: Optional[int] = None
    numero_orcamento: str
    data_validade: date
    status: str
    subtotal: Optional[Decimal] = None
    desconto: Optional[Decimal] = None
    acrescimo: Optional[Decimal] = None
    total: Optional[Decimal] = None
    observacoes: Optional[str] = None
    condicoes_pagamento: Optional[str] = None
    convertido_em_pedido_id: Optional[int] = None
    data_conversao: Optional[datetime] = None
    created_at: datetime
    itens: List[OrcamentoItemResponse] = []


class OrcamentoListResponse(BaseModel):
    """Item de listagem de orçamentos."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    cliente_id: int
    numero_orcamento: str
    data_validade: date
    status: str
    total: Optional[Decimal] = None
    convertido_em_pedido_id: Optional[int] = None
    created_at: datetime


class OrcamentoConverterRequest(BaseModel):
    """Body para conversão orçamento → pedido."""
    reservar_estoque: bool = Field(False, description="Se true, reserva estoque ao criar o pedido")
