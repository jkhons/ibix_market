# PDV Ibix - Schemas de Pedido
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PedidoItemCreate(BaseModel):
    """Item para criação de pedido."""
    produto_cliente_id: int = Field(..., description="ID do produto (produtos_cliente)")
    quantidade: float = Field(..., gt=0)
    preco_unitario: float = Field(..., ge=0)
    desconto_percentual: Optional[float] = Field(None, ge=0, le=100)
    desconto_valor: Optional[float] = Field(None, ge=0)
    observacao_item: Optional[str] = None


class PedidoItemResponse(BaseModel):
    """Item de pedido na resposta."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    pedido_id: int
    produto_cliente_id: int
    codigo_produto: Optional[str] = None
    descricao_produto: Optional[str] = None
    quantidade: Decimal
    quantidade_faturada: Decimal
    preco_unitario: Decimal
    desconto_percentual: Optional[Decimal] = None
    desconto_valor: Optional[Decimal] = None
    total_item: Decimal
    status: str


class PedidoCreate(BaseModel):
    """Criação de pedido (direto, sem orçamento)."""
    cliente_id: int = Field(..., description="Estabelecimento")
    orcamento_id: Optional[int] = Field(None, description="Se veio de orçamento, preenchido na conversão")
    data_prevista_entrega: Optional[date] = None
    observacoes: Optional[str] = None
    itens: List[PedidoItemCreate] = Field(..., min_length=1)


class PedidoUpdate(BaseModel):
    """Atualização parcial de pedido."""
    data_prevista_entrega: Optional[date] = None
    observacoes: Optional[str] = None
    status: Optional[str] = None
    itens: Optional[List[PedidoItemCreate]] = None


class PedidoResponse(BaseModel):
    """Pedido na resposta."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    orcamento_id: Optional[int] = None
    venda_id: Optional[int] = None
    cliente_id: int
    vendedor_id: Optional[int] = None
    numero_pedido: str
    data_pedido: Optional[datetime] = None
    data_prevista_entrega: Optional[date] = None
    status: str
    reserva_estoque: bool
    data_reserva: Optional[datetime] = None
    subtotal: Optional[Decimal] = None
    desconto: Optional[Decimal] = None
    acrescimo: Optional[Decimal] = None
    total: Optional[Decimal] = None
    observacoes: Optional[str] = None
    created_at: datetime
    itens: List[PedidoItemResponse] = []


class PedidoListResponse(BaseModel):
    """Item de listagem de pedidos."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    cliente_id: int
    numero_pedido: str
    data_pedido: Optional[datetime] = None
    status: str
    total: Optional[Decimal] = None
    orcamento_id: Optional[int] = None
    created_at: datetime


class PedidoFaturarRequest(BaseModel):
    """Item para faturamento parcial: qual item e quanto faturar."""
    pedido_item_id: int = Field(..., description="ID do pedido_item")
    quantidade: float = Field(..., gt=0, description="Quantidade a faturar neste lote")


class PedidoFaturarBody(BaseModel):
    """Body para faturamento (parcial ou total)."""
    itens: List[PedidoFaturarRequest] = Field(..., min_length=1)
