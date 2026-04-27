# PDV Ibix - Schemas de Notas de Serviço (NFS-e)
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class StatusNotaServicoEnum(str, Enum):
    """Enum para status da nota de serviço"""
    PENDENTE = "pendente"
    AUTORIZADO = "autorizado"
    CANCELADO = "cancelado"
    REJEITADO = "rejeitado"

# Schemas para Itens
class NotaServicoItemBase(BaseModel):
    """Schema base para item de nota de serviço"""
    item_numero: int = Field(..., ge=1, description="Número sequencial do item na NFS-e")
    discriminacao: str = Field(..., min_length=1, description="Discriminação do serviço")
    codigo_servico_municipal: Optional[str] = Field(None, max_length=20, description="Código de serviço municipal (LC 116)")
    codigo_cnae: Optional[str] = Field(None, max_length=20, description="Código CNAE do serviço")
    
    quantidade: Optional[Decimal] = Field(None, gt=0, description="Quantidade do serviço")
    valor_unitario: Optional[Decimal] = Field(None, ge=0, description="Valor unitário do serviço")
    valor_total: Decimal = Field(..., ge=0, description="Valor total do item")
    
    aliquota_iss: Optional[Decimal] = Field(None, description="Alíquota do ISS (%)")
    valor_iss: Decimal = Field(0.00, ge=0, description="Valor do ISS")
    base_calculo_iss: Decimal = Field(0.00, ge=0, description="Base de cálculo do ISS")

class NotaServicoItemCreate(NotaServicoItemBase):
    """Schema para criação de item de nota de serviço"""
    pass

class NotaServicoItemResponse(NotaServicoItemBase):
    """Schema para resposta de item de nota de serviço"""
    id: int
    nota_servico_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Schemas para Nota de Serviço
class NotaServicoBase(BaseModel):
    """Schema base para nota de serviço"""
    numero: str = Field(..., min_length=1, max_length=20, description="Número da NFS-e")
    codigo_verificacao: Optional[str] = Field(None, max_length=20, description="Código de verificação da NFS-e")
    
    data_emissao: datetime = Field(..., description="Data e hora de emissão da NFS-e")
    data_competencia: Optional[date] = Field(None, description="Data de competência do serviço")
    
    cliente_id: Optional[int] = Field(None, description="ID do cliente")
    empresa_id: int = Field(..., description="ID da empresa emissora")
    venda_id: Optional[int] = Field(None, description="ID da venda relacionada (opcional)")
    emitido_por_id: int = Field(..., description="ID do usuário que emitiu a nota")
    
    valor_total: Decimal = Field(..., ge=0, description="Valor total da NFS-e")
    valor_servicos: Decimal = Field(0.00, ge=0, description="Valor dos serviços")
    valor_deducoes: Decimal = Field(0.00, ge=0, description="Valor das deduções")
    valor_desconto: Decimal = Field(0.00, ge=0, description="Valor de desconto")
    
    valor_iss: Decimal = Field(0.00, ge=0, description="Valor do ISS")
    aliquota_iss: Optional[Decimal] = Field(None, description="Alíquota do ISS (%)")
    base_calculo_iss: Decimal = Field(0.00, ge=0, description="Base de cálculo do ISS")
    valor_pis: Decimal = Field(0.00, ge=0, description="Valor do PIS")
    valor_cofins: Decimal = Field(0.00, ge=0, description="Valor do COFINS")
    valor_inss: Decimal = Field(0.00, ge=0, description="Valor do INSS")
    valor_ir: Decimal = Field(0.00, ge=0, description="Valor do IR (Imposto de Renda)")
    valor_csll: Decimal = Field(0.00, ge=0, description="Valor do CSLL (Contribuição Social sobre Lucro Líquido)")
    
    codigo_servico_municipal: Optional[str] = Field(None, max_length=20, description="Código de serviço municipal (LC 116)")
    codigo_tributacao_municipio: Optional[str] = Field(None, max_length=20, description="Código de tributação no município")
    discriminacao_servicos: str = Field(..., min_length=1, description="Discriminação detalhada dos serviços prestados")
    local_prestacao: Optional[str] = Field(None, max_length=255, description="Local de prestação do serviço")
    municipio_prestacao: Optional[str] = Field(None, max_length=100, description="Município de prestação do serviço")
    uf_prestacao: Optional[str] = Field(None, max_length=2, description="UF de prestação do serviço")
    
    status: StatusNotaServicoEnum = Field(StatusNotaServicoEnum.PENDENTE, description="Status da NFS-e")
    protocolo_autorizacao: Optional[str] = Field(None, max_length=50, description="Protocolo de autorização retornado pela API municipal")
    data_autorizacao: Optional[datetime] = Field(None, description="Data e hora da autorização")
    mensagem_retorno: Optional[str] = Field(None, description="Mensagem retornada pela API municipal")
    
    xml_path: Optional[str] = Field(None, max_length=255, description="Caminho do arquivo XML da NFS-e")
    pdf_path: Optional[str] = Field(None, max_length=255, description="Caminho do arquivo PDF da NFS-e")

class NotaServicoCreate(NotaServicoBase):
    """Schema para criação de nota de serviço"""
    itens: List[NotaServicoItemCreate] = Field(..., min_items=1, description="Itens da nota de serviço")

class NotaServicoUpdate(BaseModel):
    """Schema para atualização de nota de serviço"""
    status: Optional[StatusNotaServicoEnum] = None
    protocolo_autorizacao: Optional[str] = Field(None, max_length=50)
    data_autorizacao: Optional[datetime] = None
    mensagem_retorno: Optional[str] = None
    xml_path: Optional[str] = Field(None, max_length=255)
    pdf_path: Optional[str] = Field(None, max_length=255)

class NotaServicoResponse(NotaServicoBase):
    """Schema para resposta de nota de serviço"""
    id: int
    itens: List[NotaServicoItemResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

