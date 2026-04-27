# PDV Ibix - Schemas de Notas Fiscais (NF-e / NFC-e)
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class TipoNotaEnum(str, Enum):
    """Enum para tipo de nota fiscal"""
    NFE = "NFe"
    NFCE = "NFCe"

class StatusNotaEnum(str, Enum):
    """Enum para status da nota fiscal (alinhado ao modelo)"""
    RASCUNHO = "rascunho"
    PENDENTE = "pendente"
    ENVIADA = "enviada"
    AUTORIZADO = "autorizado"
    CANCELADO = "cancelado"
    REJEITADO = "rejeitado"
    DENEGADO = "denegado"


class OrigemDocumentoFiscalEnum(str, Enum):
    """Origem do documento fiscal (alinhado ao modelo)"""
    MANUAL = "manual"
    ORCAMENTO = "orcamento"
    VENDA_BALCAO = "venda_balcao"
    ORDEM_SERVICO = "ordem_servico"
    VENDA_MARKETPLACE = "venda_marketplace"

class AmbienteEnum(str, Enum):
    """Enum para ambiente de emissão"""
    HOMOLOGACAO = "homologacao"
    PRODUCAO = "producao"

# Schemas para Itens
class NotaFiscalItemBase(BaseModel):
    """Schema base para item de nota fiscal"""
    item_numero: int = Field(..., ge=1, description="Número sequencial do item na nota fiscal")
    descricao: str = Field(..., min_length=1, max_length=255, description="Descrição do produto/serviço")
    codigo_produto: Optional[str] = Field(None, max_length=50, description="Código interno do produto")
    ncm: Optional[str] = Field(None, max_length=10, description="Nomenclatura Comum do Mercosul")
    cest: Optional[str] = Field(None, max_length=10, description="Código Especificador de Substituição Tributária")
    cfop: Optional[str] = Field(None, max_length=10, description="CFOP da operação")
    unidade: str = Field(..., min_length=1, max_length=10, description="Unidade de medida (UN, KG, etc.)")
    extipi: Optional[str] = Field(None, max_length=5, description="EX TIPI (código específico da TIPI)")
    
    quantidade: Decimal = Field(..., gt=0, description="Quantidade do item")
    valor_unitario: Decimal = Field(..., ge=0, description="Valor unitário do item")
    valor_total: Decimal = Field(..., ge=0, description="Valor total do item")
    valor_desconto: Decimal = Field(0.00, ge=0, description="Valor de desconto do item")
    
    origem: Optional[int] = Field(None, ge=0, le=8, description="Origem da mercadoria (0-8)")
    cst_icms: Optional[str] = Field(None, max_length=5, description="CST ICMS (regime normal)")
    csosn: Optional[str] = Field(None, max_length=5, description="CSOSN (Simples Nacional)")
    aliquota_icms: Optional[Decimal] = Field(None, description="Alíquota do ICMS (%)")
    valor_icms: Decimal = Field(0.00, ge=0, description="Valor do ICMS")
    valor_base_icms: Decimal = Field(0.00, ge=0, description="Base de cálculo do ICMS")
    
    modalidade_bc_icms_st: Optional[int] = Field(None, description="Modalidade de cálculo da BC do ICMS ST")
    aliquota_icms_st: Optional[Decimal] = Field(None, description="Alíquota do ICMS ST (%)")
    valor_base_icms_st: Decimal = Field(0.00, ge=0, description="Base de cálculo do ICMS ST")
    valor_icms_st: Decimal = Field(0.00, ge=0, description="Valor do ICMS ST")
    
    ipi_cst: Optional[str] = Field(None, max_length=5, description="CST IPI")
    ipi_codigo_enquadramento: Optional[str] = Field(None, max_length=10, description="Código de enquadramento IPI")
    ipi_aliquota: Optional[Decimal] = Field(None, description="Alíquota do IPI (%)")
    valor_ipi: Decimal = Field(0.00, ge=0, description="Valor do IPI")
    valor_base_ipi: Decimal = Field(0.00, ge=0, description="Base de cálculo do IPI")
    
    pis_cst: Optional[str] = Field(None, max_length=5, description="CST PIS")
    pis_aliquota: Optional[Decimal] = Field(None, description="Alíquota do PIS (%)")
    pis_valor: Decimal = Field(0.00, ge=0, description="Valor do PIS")
    pis_base_calculo: Decimal = Field(0.00, ge=0, description="Base de cálculo do PIS")
    
    cofins_cst: Optional[str] = Field(None, max_length=5, description="CST COFINS")
    cofins_aliquota: Optional[Decimal] = Field(None, description="Alíquota do COFINS (%)")
    cofins_valor: Decimal = Field(0.00, ge=0, description="Valor do COFINS")
    cofins_base_calculo: Decimal = Field(0.00, ge=0, description="Base de cálculo do COFINS")
    
    informacoes_adicionais: Optional[str] = Field(None, description="Informações complementares do item")
    produto_cliente_id: Optional[int] = Field(None, description="ID do produto (produtos_cliente)")

class NotaFiscalItemCreate(NotaFiscalItemBase):
    """Schema para criação de item de nota fiscal"""
    pass

class NotaFiscalItemResponse(NotaFiscalItemBase):
    """Schema para resposta de item de nota fiscal"""
    id: int
    nota_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Schemas para Nota Fiscal
class NotaFiscalBase(BaseModel):
    """Schema base para nota fiscal"""
    numero: str = Field(..., min_length=1, max_length=20, description="Número sequencial da nota fiscal")
    serie: str = Field("1", max_length=10, description="Série da nota fiscal")
    tipo: TipoNotaEnum = Field(..., description="Tipo de nota (NFe ou NFCe)")
    modelo: str = Field(..., min_length=1, max_length=5, description="Modelo da nota (55=NF-e, 65=NFC-e)")
    
    data_emissao: datetime = Field(..., description="Data e hora de emissão da nota fiscal")
    data_saida: Optional[datetime] = Field(None, description="Data e hora de saída/entrada da mercadoria")
    
    cliente_id: Optional[int] = Field(None, description="ID do cliente/destinatário")
    empresa_id: int = Field(..., description="ID da empresa emissora")
    venda_id: Optional[int] = Field(None, description="ID da venda relacionada (opcional)")
    pedido_id: Optional[int] = Field(None, description="ID do pedido quando NF originada de faturamento")
    emitido_por_id: Optional[int] = Field(None, description="ID do usuário que emitiu a nota (null quando criada por task)")
    origem_documento: Optional[OrigemDocumentoFiscalEnum] = Field(None, description="Origem do documento (manual, orcamento, venda_balcao, ordem_servico, venda_marketplace)")
    
    valor_total: Decimal = Field(..., ge=0, description="Valor total da nota fiscal")
    valor_produtos: Decimal = Field(0.00, ge=0, description="Valor total dos produtos")
    valor_frete: Decimal = Field(0.00, ge=0, description="Valor do frete")
    valor_seguro: Decimal = Field(0.00, ge=0, description="Valor do seguro")
    valor_desconto: Decimal = Field(0.00, ge=0, description="Valor total de desconto")
    valor_outros: Decimal = Field(0.00, ge=0, description="Valor de outras despesas")
    
    valor_icms: Decimal = Field(0.00, ge=0, description="Valor total do ICMS")
    valor_icms_desonerado: Decimal = Field(0.00, ge=0, description="Valor do ICMS desonerado")
    valor_icms_st: Decimal = Field(0.00, ge=0, description="Valor do ICMS Substituição Tributária")
    valor_ipi: Decimal = Field(0.00, ge=0, description="Valor total do IPI")
    valor_pis: Decimal = Field(0.00, ge=0, description="Valor total do PIS")
    valor_cofins: Decimal = Field(0.00, ge=0, description="Valor total do COFINS")
    
    chave_acesso: Optional[str] = Field(None, max_length=44, description="Chave de acesso da NF-e (44 dígitos)")
    protocolo_autorizacao: Optional[str] = Field(None, max_length=50, description="Protocolo de autorização retornado pela SEFAZ")
    data_autorizacao: Optional[datetime] = Field(None, description="Data e hora da autorização pela SEFAZ")
    ambiente: AmbienteEnum = Field(AmbienteEnum.HOMOLOGACAO, description="Ambiente de emissão")
    status: StatusNotaEnum = Field(StatusNotaEnum.RASCUNHO, description="Status da nota fiscal (rascunho ao criar)")
    codigo_status: Optional[str] = Field(None, max_length=10, description="Código do status retornado pela SEFAZ")
    mensagem_retorno: Optional[str] = Field(None, description="Mensagem retornada pela SEFAZ")
    
    xml_path: Optional[str] = Field(None, max_length=255, description="Caminho do arquivo XML assinado")
    xml_retorno_path: Optional[str] = Field(None, max_length=255, description="Caminho do arquivo XML de retorno da SEFAZ")
    danfe_path: Optional[str] = Field(None, max_length=255, description="Caminho do arquivo DANFE em PDF")
    qr_code_url: Optional[str] = Field(None, max_length=500, description="URL do QR Code (para NFC-e)")
    qr_code_image_path: Optional[str] = Field(None, max_length=255, description="Caminho da imagem do QR Code")
    
    natureza_operacao: Optional[str] = Field(None, max_length=100, description="Natureza da operação")
    forma_pagamento: Optional[str] = Field(None, max_length=50, description="Forma de pagamento (para NFC-e)")
    tipo_pagamento: Optional[str] = Field(None, max_length=50, description="Tipo de pagamento")
    observacoes: Optional[str] = Field(None, description="Observações gerais")
    informacoes_complementares: Optional[str] = Field(None, description="Informações complementares da nota fiscal")

class NotaFiscalCreate(NotaFiscalBase):
    """Schema para criação de nota fiscal"""
    itens: List[NotaFiscalItemCreate] = Field(..., min_length=1, description="Itens da nota fiscal")

class NotaFiscalUpdate(BaseModel):
    """Schema para atualização de nota fiscal"""
    status: Optional[StatusNotaEnum] = None
    protocolo_autorizacao: Optional[str] = Field(None, max_length=50)
    data_autorizacao: Optional[datetime] = None
    codigo_status: Optional[str] = Field(None, max_length=10)
    mensagem_retorno: Optional[str] = None
    xml_path: Optional[str] = Field(None, max_length=255)
    xml_retorno_path: Optional[str] = Field(None, max_length=255)
    danfe_path: Optional[str] = Field(None, max_length=255)
    qr_code_url: Optional[str] = Field(None, max_length=500)
    qr_code_image_path: Optional[str] = Field(None, max_length=255)

class NotaFiscalResponse(NotaFiscalBase):
    """Schema para resposta de nota fiscal"""
    id: int
    itens: List[NotaFiscalItemResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Dados relacionados para exibição
    cliente: Optional[dict] = None
    empresa: Optional[dict] = None

    @field_validator("empresa", mode="before")
    @classmethod
    def _empresa_to_dict(cls, v: Any) -> Any:
        """Converte ORM Empresa para dict na resposta."""
        if v is None or isinstance(v, dict):
            return v
        if hasattr(v, "id"):
            return {
                "id": v.id,
                "razao_social": getattr(v, "razao_social", None),
                "nome_fantasia": getattr(v, "nome_fantasia", None),
                "cnpj": getattr(v, "cnpj", None),
            }
        return v

    @field_validator("cliente", mode="before")
    @classmethod
    def _cliente_to_dict(cls, v: Any) -> Any:
        """Converte ORM Cliente para dict na resposta."""
        if v is None or isinstance(v, dict):
            return v
        if hasattr(v, "id"):
            return {
                "id": v.id,
                "nome": getattr(v, "nome", None),
                "razao_social": getattr(v, "razao_social", None) or getattr(v, "nome", None),
                "cnpj": getattr(v, "cnpj", None),
                "cpf": getattr(v, "cpf", None),
            }
        return v

    @field_validator("origem_documento", mode="before")
    @classmethod
    def _normalize_origem_documento(cls, v: Any) -> Any:
        """Aceita enum do modelo (ex.: VENDA_MARKETPLACE) convertendo pelo value."""
        if v is None:
            return None
        if isinstance(v, OrigemDocumentoFiscalEnum):
            return v
        if getattr(v, "value", None) is not None:
            val = getattr(v, "value")
            for e in OrigemDocumentoFiscalEnum:
                if e.value == val:
                    return e
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, v: Any) -> Any:
        """Aceita status vindo do DB como str (ex. 'AUTORIZADO') e normaliza para enum."""
        if v is None:
            return StatusNotaEnum.RASCUNHO
        if isinstance(v, StatusNotaEnum):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            for e in StatusNotaEnum:
                if e.value == s:
                    return e
        return v

    @field_validator("tipo", mode="before")
    @classmethod
    def _normalize_tipo(cls, v: Any) -> Any:
        """Aceita tipo vindo do DB como str."""
        if v is None:
            return TipoNotaEnum.NFE
        if isinstance(v, TipoNotaEnum):
            return v
        if isinstance(v, str):
            u = v.strip()
            for e in TipoNotaEnum:
                if e.value == u or e.value.upper() == u.upper():
                    return e
        return v

    @field_validator("ambiente", mode="before")
    @classmethod
    def _normalize_ambiente(cls, v: Any) -> Any:
        """Aceita ambiente vindo do DB como str."""
        if v is None:
            return AmbienteEnum.HOMOLOGACAO
        if isinstance(v, AmbienteEnum):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            for e in AmbienteEnum:
                if e.value == s:
                    return e
        return v

    class Config:
        from_attributes = True


class CancelarNotaBody(BaseModel):
    """Body para cancelamento de nota fiscal (justificativa mínima 15 caracteres)"""
    justificativa: str = Field(..., min_length=15, description="Justificativa do cancelamento")

