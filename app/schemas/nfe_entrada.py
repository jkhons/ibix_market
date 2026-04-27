# PDV Ibix - Schemas Entrada de Notas NFe (importação XML)
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NfeDocumentoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cliente_id: int
    chave_acesso_44: str
    modelo: Optional[str] = None
    serie: Optional[str] = None
    numero: Optional[str] = None
    emissao_em: Optional[datetime] = None
    entrada_saida: str
    ambiente: Optional[str] = None
    emitente_fornecedor_id: Optional[int] = None
    emitente_nome: Optional[str] = None  # Nome/razão do emissor (preenchido na listagem a partir do fornecedor)
    total_produtos: Optional[Decimal] = None
    total_nota: Optional[Decimal] = None
    status: str
    created_at: datetime
    updated_at: datetime
    total_itens: Optional[int] = None
    itens_vinculados: Optional[int] = None


class NfeItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nfe_id: int
    numero_item: Optional[int] = None
    cprod_xml: Optional[str] = None
    xprod_xml: Optional[str] = None
    ean_xml: Optional[str] = None
    ncm_xml: Optional[str] = None
    cfop_xml: Optional[str] = None
    ucom_xml: Optional[str] = None
    qcom_xml: Optional[Decimal] = None
    vuncom_xml: Optional[Decimal] = None
    vprod_xml: Optional[Decimal] = None
    vdesc_xml: Optional[Decimal] = None
    vfrete_xml: Optional[Decimal] = None
    vseg_xml: Optional[Decimal] = None
    voutro_xml: Optional[Decimal] = None
    vipi_xml: Optional[Decimal] = None
    vicmsst_xml: Optional[Decimal] = None
    cest_xml: Optional[str] = None
    extipi_xml: Optional[str] = None
    infadprod_xml: Optional[str] = None
    orig_xml: Optional[int] = None
    produto_cliente_id: Optional[int] = None
    fornecedor_id: Optional[int] = None
    conciliar_status: str
    created_at: datetime
    updated_at: datetime


class NfeItemVincularBody(BaseModel):
    produto_cliente_id: int = Field(..., description="ID do produto interno (produtos_cliente) a vincular")


class NfeImportResponse(BaseModel):
    documento: NfeDocumentoResponse
    avisos: List[dict] = Field(default_factory=list)


class NfeImportLoteItemResult(BaseModel):
    arquivo: str
    sucesso: bool
    erro: Optional[str] = None
    documento: Optional[NfeDocumentoResponse] = None
    avisos: List[dict] = Field(default_factory=list)


class NfeImportLoteResponse(BaseModel):
    resultados: List[NfeImportLoteItemResult]
    total_ok: int = 0
    total_erro: int = 0


class NfeConfirmarLancarResponse(BaseModel):
    movimentacoes_criadas: int
    mensagem: str = "Nota conciliada e lançada no estoque."
