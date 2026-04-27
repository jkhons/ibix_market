# PDV Ibix - Schemas de Cupons Fiscais (CF-e - SAT/MFe)
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TipoEquipamentoEnum(str, Enum):
    """Enum para tipo de equipamento SAT/MFe"""
    SAT = "SAT"
    MFE = "MFe"

class StatusCupomEnum(str, Enum):
    """Enum para status do cupom fiscal"""
    PENDENTE = "pendente"
    AUTORIZADO = "autorizado"
    CANCELADO = "cancelado"
    REJEITADO = "rejeitado"

# Schemas para Itens
class CupomFiscalItemBase(BaseModel):
    """Schema base para item de cupom fiscal"""
    item_numero: int = Field(..., ge=1, description="Número sequencial do item no CF-e")
    codigo_produto: Optional[str] = Field(None, max_length=50, description="Código interno do produto")
    descricao: str = Field(..., min_length=1, max_length=255, description="Descrição do produto")
    ncm: Optional[str] = Field(None, max_length=10, description="Nomenclatura Comum do Mercosul")
    cfop: Optional[str] = Field(None, max_length=10, description="CFOP da operação")
    unidade: Optional[str] = Field(None, max_length=10, description="Unidade de medida")
    
    quantidade: Decimal = Field(..., gt=0, description="Quantidade do item")
    valor_unitario: Decimal = Field(..., ge=0, description="Valor unitário do item")
    valor_total: Decimal = Field(..., ge=0, description="Valor total do item")
    valor_desconto: Decimal = Field(0.00, ge=0, description="Valor de desconto do item")
    
    cst_icms: Optional[str] = Field(None, max_length=5, description="CST ICMS")
    aliquota_icms: Optional[Decimal] = Field(None, description="Alíquota do ICMS (%)")
    valor_icms: Decimal = Field(0.00, ge=0, description="Valor do ICMS")
    
    produto_cliente_id: Optional[int] = Field(None, description="ID do produto (produtos_cliente)")

class CupomFiscalItemCreate(CupomFiscalItemBase):
    """Schema para criação de item de cupom fiscal"""
    pass

class CupomFiscalItemResponse(CupomFiscalItemBase):
    """Schema para resposta de item de cupom fiscal"""
    id: int
    cupom_fiscal_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Schemas para Cupom Fiscal
class CupomFiscalBase(BaseModel):
    """Schema base para cupom fiscal"""
    numero_cfe: str = Field(..., min_length=1, max_length=20, description="Número do CF-e")
    serie: Optional[str] = Field(None, max_length=10, description="Série do CF-e")
    chave_cfe: Optional[str] = Field(None, max_length=50, description="Chave de acesso do CF-e")
    
    data_emissao: datetime = Field(..., description="Data e hora de emissão do CF-e")
    
    cliente_id: Optional[int] = Field(None, description="ID do cliente (pode ser NULL para consumidor final)")
    empresa_id: int = Field(..., description="ID da empresa emissora")
    venda_id: Optional[int] = Field(None, description="ID da venda relacionada (opcional)")
    emitido_por_id: int = Field(..., description="ID do usuário que emitiu o cupom")
    
    valor_total: Decimal = Field(..., ge=0, description="Valor total do CF-e")
    valor_produtos: Decimal = Field(0.00, ge=0, description="Valor total dos produtos")
    valor_desconto: Decimal = Field(0.00, ge=0, description="Valor de desconto")
    valor_acrescimo: Decimal = Field(0.00, ge=0, description="Valor de acréscimo")
    valor_troco: Decimal = Field(0.00, ge=0, description="Valor do troco")
    
    tipo_equipamento: TipoEquipamentoEnum = Field(..., description="Tipo de equipamento (SAT ou MFe)")
    numero_serie_sat: Optional[str] = Field(None, max_length=100, description="Número de série do equipamento SAT/MFe")
    codigo_ativacao: Optional[str] = Field(None, max_length=100, description="Código de ativação do equipamento")
    numero_caixa: Optional[int] = Field(None, description="Número do ECF (caixa)")
    
    status: StatusCupomEnum = Field(StatusCupomEnum.PENDENTE, description="Status do CF-e")
    protocolo_autorizacao: Optional[str] = Field(None, max_length=50, description="Protocolo de autorização retornado pelo equipamento")
    data_autorizacao: Optional[datetime] = Field(None, description="Data e hora da autorização")
    mensagem_retorno: Optional[str] = Field(None, description="Mensagem retornada pelo equipamento")
    
    xml_sat_path: Optional[str] = Field(None, max_length=255, description="Caminho do arquivo XML do SAT/MFe")
    extrato_path: Optional[str] = Field(None, max_length=255, description="Caminho do arquivo extrato do CF-e")
    qr_code_url: Optional[str] = Field(None, max_length=500, description="URL do QR Code do CF-e")
    qr_code_image_path: Optional[str] = Field(None, max_length=255, description="Caminho da imagem do QR Code")
    
    forma_pagamento: Optional[str] = Field(None, max_length=50, description="Forma de pagamento")
    tipo_pagamento: Optional[str] = Field(None, max_length=50, description="Tipo de pagamento")

class CupomFiscalCreate(CupomFiscalBase):
    """Schema para criação de cupom fiscal"""
    itens: List[CupomFiscalItemCreate] = Field(..., min_items=1, description="Itens do cupom fiscal")

class CupomFiscalUpdate(BaseModel):
    """Schema para atualização de cupom fiscal"""
    status: Optional[StatusCupomEnum] = None
    protocolo_autorizacao: Optional[str] = Field(None, max_length=50)
    data_autorizacao: Optional[datetime] = None
    mensagem_retorno: Optional[str] = None
    xml_sat_path: Optional[str] = Field(None, max_length=255)
    extrato_path: Optional[str] = Field(None, max_length=255)
    qr_code_url: Optional[str] = Field(None, max_length=500)
    qr_code_image_path: Optional[str] = Field(None, max_length=255)

class CupomFiscalResponse(CupomFiscalBase):
    """Schema para resposta de cupom fiscal"""
    id: int
    itens: List[CupomFiscalItemResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

