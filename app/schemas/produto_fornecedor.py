# PDV Ibix - Schemas ProdutoFornecedor (vínculo produto ↔ fornecedor)
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProdutoFornecedorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    produto_cliente_id: int
    fornecedor_cliente_id: int
    codigo_fornecedor: Optional[str] = None
    preco_compra: Optional[Decimal] = None
    xprod_amostra: Optional[str] = None
    ean_amostra: Optional[str] = None
    ucom_amostra: Optional[str] = None
    fator_conversao: Decimal
    ativo: bool
    created_at: datetime
    produto_nome: Optional[str] = None
    produto_codigo: Optional[str] = None
