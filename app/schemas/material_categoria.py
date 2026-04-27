# PDV Ibix - Schemas Material Categoria (estoque)
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MaterialCategoriaBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    codigo: str
    icone: Optional[str] = None
    ativo: bool = True
    controla_estoque: bool = True
    permite_negativo: bool = False
    tem_validade: bool = False
    dias_alerta_vencimento: int = 30
    requer_aprovacao: bool = False
    limite_movimentacao: Optional[Decimal] = None
    incluir_relatorios: bool = True
    cor_relatorio: str = "#007bff"


class MaterialCategoriaCreate(MaterialCategoriaBase):
    pass


class MaterialCategoriaUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    codigo: Optional[str] = None
    icone: Optional[str] = None
    ativo: Optional[bool] = None
    controla_estoque: Optional[bool] = None
    permite_negativo: Optional[bool] = None
    tem_validade: Optional[bool] = None
    dias_alerta_vencimento: Optional[int] = None
    requer_aprovacao: Optional[bool] = None
    limite_movimentacao: Optional[Decimal] = None
    incluir_relatorios: Optional[bool] = None
    cor_relatorio: Optional[str] = None


class MaterialCategoriaResponse(MaterialCategoriaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
