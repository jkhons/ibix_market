# PDV Ibix — Superadmin: linhas de compra PDV + vitrine (agregado)
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CompraGlobalLinha(BaseModel):
    """Uma linha de item de compra (PDV ou marketplace)."""

    origem: str = Field(..., description="pdv | vitrine")
    linha_id: int = Field(..., description="ID do venda_itens ou pedido_itens_marketplace")
    data_ref: datetime = Field(..., description="Data da venda ou do pedido")
    estabelecimento_cliente_id: int
    estabelecimento_nome: Optional[str] = None
    cliente_id: Optional[int] = Field(
        None,
        description="clientes.id do comprador (PDV); marketplace pode ser null",
    )
    comprador_nome: str
    comprador_email: Optional[str] = None
    produto_nome: str
    categoria: Optional[str] = None
    quantidade: Decimal = Field(..., description="Quantidade no item")
    valor_total_item: Decimal
    documento_ref: str = Field(..., description="numero_venda ou numero_pedido")
    venda_ou_pedido_id: int = Field(..., description="vendas.id ou pedidos_marketplace.id")
    atribuicao: Optional[Dict[str, Any]] = Field(
        None,
        description="Marketplace: utm_*, canal_origem, aceite_marketing_snapshot",
    )
    cookies: Optional[Dict[str, Any]] = Field(
        None,
        description="Reservado para consentimento/cookies de navegação (ainda não persistido).",
    )


class CompraGlobalListResponse(BaseModel):
    items: List[CompraGlobalLinha]
    total: int
    skip: int
    limit: int
