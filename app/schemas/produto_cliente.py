# PDV Ibix - Schemas Produto por Estabelecimento (Fase 2)
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ProdutoClienteBase(BaseModel):
    cliente_id: int
    codigo: str
    nome: str
    descricao: Optional[str] = None
    ncm: Optional[str] = None
    cfop_padrao: Optional[str] = None
    cest: Optional[str] = None
    extipi: Optional[str] = None
    origem_mercadoria: Optional[int] = None
    referencia: Optional[str] = None
    unidade_medida: str = "UN"
    valor_custo: Optional[Decimal] = None
    valor_venda: Optional[Decimal] = None
    quantidade_minima: Optional[Decimal] = None
    quantidade_maxima: Optional[Decimal] = None
    ativo: bool = True
    controla_estoque: bool = True
    categoria: Optional[str] = None
    tipo_material: Optional[str] = None
    tipo_material_id: Optional[int] = None
    categoria_id: Optional[int] = None
    fabricante: Optional[str] = None
    fornecedor: Optional[str] = None
    data_validade: Optional[date] = None
    data_fabricacao: Optional[date] = None
    foto_peca: Optional[str] = None
    midias: Optional[list] = None  # lista de { "tipo": "imagem"|"video", "url": str }
    codigo_barras: Optional[str] = None  # GTIN principal (8, 12, 13 ou 14 dígitos); persistido em codigos_barras_cliente


class ProdutoClienteCreate(ProdutoClienteBase):
    quantidade_atual: Optional[Decimal] = 0
    foto_peca_base64: Optional[str] = None  # data URL ou base64; não persiste no model, gera foto_peca no backend


class ProdutoClienteUpdate(BaseModel):
    codigo: Optional[str] = None
    nome: Optional[str] = None
    descricao: Optional[str] = None
    ncm: Optional[str] = None
    cfop_padrao: Optional[str] = None
    cest: Optional[str] = None
    extipi: Optional[str] = None
    origem_mercadoria: Optional[int] = None
    referencia: Optional[str] = None
    unidade_medida: Optional[str] = None
    valor_custo: Optional[Decimal] = None
    valor_venda: Optional[Decimal] = None
    quantidade_atual: Optional[Decimal] = None
    quantidade_minima: Optional[Decimal] = None
    quantidade_maxima: Optional[Decimal] = None
    ativo: Optional[bool] = None
    controla_estoque: Optional[bool] = None
    categoria: Optional[str] = None
    tipo_material: Optional[str] = None
    tipo_material_id: Optional[int] = None
    categoria_id: Optional[int] = None
    fabricante: Optional[str] = None
    fornecedor: Optional[str] = None
    data_validade: Optional[date] = None
    data_fabricacao: Optional[date] = None
    foto_peca: Optional[str] = None
    midias: Optional[list] = None
    foto_peca_base64: Optional[str] = None  # data URL ou base64; não persiste, gera foto_peca no backend
    codigo_barras: Optional[str] = None  # GTIN principal; ao enviar, atualiza codigos_barras_cliente


class ProdutoClienteResponse(ProdutoClienteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    quantidade_atual: Decimal
    cliente_nome: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("midias", mode="before")
    @classmethod
    def midias_parse(cls, v: Any) -> Optional[list]:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str) and v.strip():
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return None
