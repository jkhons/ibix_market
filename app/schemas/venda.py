# PDV Ibix - Schemas de Venda
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, validator


class VendaItemCreate(BaseModel):
    """Schema para criação de item de venda. Usar produto_cliente_id (produto do estabelecimento)."""
    produto_cliente_id: int = Field(..., description="ID do produto no estabelecimento (produtos_cliente)")
    quantidade: float = Field(..., gt=0, description="Quantidade vendida")
    valor_unitario: float = Field(..., ge=0, description="Valor unitário do produto")
    valor_total: float = Field(..., ge=0, description="Valor total do item")
    desconto_item: float = Field(0.0, ge=0, description="Desconto aplicado no item")
    observacoes: Optional[str] = Field(None, description="Observações do item")

    @validator('valor_total')
    def validate_valor_total(cls, v, values):
        """Validar se valor_total = quantidade * valor_unitario - desconto_item"""
        if 'quantidade' in values and 'valor_unitario' in values and 'desconto_item' in values:
            expected = values['quantidade'] * values['valor_unitario'] - values['desconto_item']
            if abs(v - expected) > 0.01:  # Tolerância para arredondamento
                raise ValueError(f"Valor total deve ser {expected:.2f}, recebido {v:.2f}")
        return v

class VendaCreate(BaseModel):
    """Schema para criação de venda"""
    cliente_id: Optional[int] = Field(None, description="ID do cliente (opcional)")
    abertura_caixa_id: int = Field(..., description="Turno de caixa aberto (obrigatório)")
    tipo_pagamento: str = Field(..., description="Tipo de pagamento")
    observacoes: Optional[str] = Field(None, description="Observações da venda")
    subtotal: float = Field(..., ge=0, description="Subtotal da venda")
    desconto: float = Field(0.0, ge=0, description="Desconto geral da venda")
    acrescimo: float = Field(0.0, ge=0, description="Acréscimo geral da venda")
    total: float = Field(..., ge=0, description="Total da venda")
    valor_pago: float = Field(..., ge=0, description="Valor pago pelo cliente")
    troco: float = Field(0.0, ge=0, description="Valor do troco")
    itens: List[VendaItemCreate] = Field(..., min_items=1, description="Itens da venda")
    
    @validator('tipo_pagamento')
    def validate_tipo_pagamento(cls, v):
        """Validar tipo de pagamento (inclui vale e crediário para fracionamento)."""
        tipos_validos = ['dinheiro', 'cartao_credito', 'cartao_debito', 'pix', 'boleto', 'transferencia', 'vale', 'crediario']
        if v not in tipos_validos:
            raise ValueError(f'Tipo de pagamento deve ser um de: {", ".join(tipos_validos)}')
        return v
    
    @validator('total')
    def validate_total(cls, v, values):
        """Validar se total = subtotal - desconto + acrescimo"""
        if 'subtotal' in values and 'desconto' in values and 'acrescimo' in values:
            expected = values['subtotal'] - values['desconto'] + values['acrescimo']
            if abs(v - expected) > 0.01:  # Tolerância para arredondamento
                raise ValueError(f"Total deve ser {expected:.2f}, recebido {v:.2f}")
        return v
    
    @validator('troco')
    def validate_troco(cls, v, values):
        """Validar se troco = valor_pago - total"""
        if 'valor_pago' in values and 'total' in values:
            expected = values['valor_pago'] - values['total']
            if abs(v - expected) > 0.01:  # Tolerância para arredondamento
                raise ValueError(f"Troco deve ser {expected:.2f}, recebido {v:.2f}")
        return v
    
    @validator('itens')
    def validate_itens_total(cls, v, values):
        """Validar se subtotal = soma dos itens"""
        if v:
            itens_subtotal = sum(item.valor_total for item in v)
            if 'subtotal' in values:
                if abs(itens_subtotal - values['subtotal']) > 0.01:
                    raise ValueError(f"Subtotal dos itens ({itens_subtotal:.2f}) não confere com subtotal ({values['subtotal']:.2f})")
        return v

class VendaItemResponse(BaseModel):
    """Schema para resposta de item de venda (produto_cliente_id)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    venda_id: int
    produto_cliente_id: Optional[int] = None
    quantidade: float
    valor_unitario: float
    valor_total: float
    desconto_item: float
    observacoes: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class VendaResponse(BaseModel):
    """Schema para resposta de venda"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_venda: str
    data_venda: datetime
    status: str
    cliente_id: Optional[int]
    abertura_caixa_id: Optional[int] = None
    caixa_id: Optional[int] = None
    caixa_identificador: Optional[str] = None
    vendedor_id: int
    subtotal: float
    desconto: float
    acrescimo: float
    total: float
    tipo_pagamento: Optional[str]
    valor_pago: float
    troco: float
    observacoes: Optional[str]
    itens: List[VendaItemResponse]
    # Relacionamentos Fiscais (opcionais)
    nota_fiscal_id: Optional[int] = None
    nota_servico_id: Optional[int] = None
    cupom_fiscal_id: Optional[int] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class VendaListResponse(BaseModel):
    """Schema para resposta de lista de vendas"""
    vendas: List[VendaResponse]
    total: int
    skip: int
    limit: int

class VendaUpdate(BaseModel):
    """Schema para atualização de venda"""
    status: Optional[str] = Field(None, description="Novo status da venda")
    observacoes: Optional[str] = Field(None, description="Observações da venda")
    
    @validator('status')
    def validate_status(cls, v):
        """Validar status da venda"""
        if v:
            status_validos = ['PENDENTE', 'CONFIRMADA', 'CANCELADA', 'FINALIZADA']
            if v not in status_validos:
                raise ValueError(f"Status deve ser um de: {', '.join(status_validos)}")
        return v

class VendaPedidoPendenteCreate(BaseModel):
    """Cria venda sem pagamento nem baixa de estoque (status PENDENTE). Finalização em POST /vendas/{id}/finalizar."""

    cliente_id: Optional[int] = Field(None, description="Cliente da venda")
    observacoes: Optional[str] = Field(None, description="Observações")
    subtotal: float = Field(..., ge=0, description="Subtotal dos itens")
    desconto: float = Field(0.0, ge=0, description="Desconto geral")
    acrescimo: float = Field(0.0, ge=0, description="Acréscimo geral")
    total: float = Field(..., ge=0, description="Total da venda")
    itens: List[VendaItemCreate] = Field(..., min_items=1, description="Itens (produto_cliente_id obrigatório)")

    @validator("total")
    def validar_total(cls, v, values):
        if "subtotal" in values and "desconto" in values and "acrescimo" in values:
            expected = values["subtotal"] - values["desconto"] + values["acrescimo"]
            if abs(v - expected) > 0.01:
                raise ValueError(f"Total deve ser {expected:.2f}, recebido {v:.2f}")
        return v

    @validator("itens")
    def validar_subtotal_itens(cls, v, values):
        if v and "subtotal" in values:
            s = sum(item.valor_total for item in v)
            if abs(s - values["subtotal"]) > 0.01:
                raise ValueError(
                    f"Subtotal dos itens ({s:.2f}) não confere com subtotal ({values['subtotal']:.2f})"
                )
        return v


class PagamentoFracionadoIn(BaseModel):
    """Uma linha de pagamento na finalização."""

    forma: str = Field(..., description="dinheiro, cartao_credito, pix, etc.")
    valor: float = Field(..., ge=0, description="Valor desta forma")


class VendaFinalizarRequest(BaseModel):
    """Conclui venda PENDENTE: turno de caixa, totais de pagamento e (opcional) fracionamento."""

    abertura_caixa_id: int = Field(..., description="Turno de caixa aberto")
    tipo_pagamento: str = Field(..., description="Forma principal (compatível com venda.tipo_pagamento)")
    valor_pago: float = Field(..., ge=0, description="Soma recebida")
    troco: float = Field(0.0, ge=0, description="Troco")
    observacoes: Optional[str] = Field(None, description="Acrescenta às observações existentes se houver")
    pagamentos: Optional[List[PagamentoFracionadoIn]] = Field(
        None,
        description="Se omitido, registra um único pagamento implícito (tipo_pagamento / valor_pago)",
    )

    @validator("tipo_pagamento")
    def validar_tipo_pagamento(cls, v):
        tipos_validos = [
            "dinheiro",
            "cartao_credito",
            "cartao_debito",
            "pix",
            "boleto",
            "transferencia",
            "vale",
            "crediario",
        ]
        if v not in tipos_validos:
            raise ValueError(f"Tipo de pagamento deve ser um de: {', '.join(tipos_validos)}")
        return v


class VendaCancelarRequest(BaseModel):
    """Cancela pedido pendente (não estorna estoque — não houve baixa)."""

    motivo: Optional[str] = Field(None, max_length=500, description="Motivo opcional")


class VendaEstornoRequest(BaseModel):
    """Schema para estorno de venda"""
    motivo: str = Field(..., min_length=3, description="Motivo do estorno da venda")
    
    @validator('motivo')
    def validate_motivo(cls, v):
        """Validar motivo do estorno"""
        if not v or len(v.strip()) < 3:
            raise ValueError("Motivo do estorno deve ter pelo menos 3 caracteres")
        return v.strip()
