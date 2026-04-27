# PDV Ibix - Schemas de Regra Fiscal ICMS
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class TipoOperacaoEnum(str, Enum):
    VENDA_INTERNA = "venda_interna"
    VENDA_INTERESTADUAL = "venda_interestadual"
    VENDA_INTERNA_ST = "venda_interna_st"
    VENDA_INTERESTADUAL_ST = "venda_interestadual_st"
    QUALQUER = "qualquer"


class TipoDestinatarioEnum(str, Enum):
    PF = "pf"
    PJ = "pj"
    QUALQUER = "qualquer"


class RegraFiscalIcmsBase(BaseModel):
    ativo: bool = True
    ordem_prioridade: int = Field(100, ge=0, le=9999)
    crt: Optional[int] = Field(None, ge=1, le=3)
    tipo_operacao: Optional[TipoOperacaoEnum] = None
    tipo_destinatario: Optional[TipoDestinatarioEnum] = None
    uf_destinatario: Optional[str] = Field(None, max_length=2)
    ncm_prefix: Optional[str] = Field(None, max_length=4)
    ncm_exato: Optional[str] = Field(None, max_length=8)
    cest: Optional[str] = Field(None, max_length=20)
    cfop_filtro: Optional[str] = Field(None, max_length=4)
    finalidade_emissao: Optional[str] = Field(None, max_length=50)
    consumidor_final: Optional[bool] = None
    contribuinte_icms: Optional[bool] = None
    vigencia_inicio: Optional[date] = None
    vigencia_fim: Optional[date] = None
    observacao_interna: Optional[str] = Field(None, max_length=2000)

    cfop: str = Field(..., min_length=4, max_length=4)
    origem_mercadoria: int = Field(..., ge=0, le=8)
    cst_icms: Optional[str] = Field(None, max_length=5)
    csosn: Optional[str] = Field(None, max_length=5)
    aliquota_icms: Decimal = Field(Decimal("0"), ge=0, le=100)
    modalidade_bc_icms: Optional[str] = Field(None, max_length=2)
    percentual_reducao_bc: Optional[Decimal] = Field(None, ge=0, le=100)
    gera_icms_st: bool = False
    aliquota_icms_st: Optional[Decimal] = Field(None, ge=0, le=100)
    modalidade_bc_icms_st: Optional[str] = Field(None, max_length=2)
    percentual_mva_st: Optional[Decimal] = Field(None, ge=0, le=1000)
    permite_credito_icms: Optional[bool] = None

    @model_validator(mode="after")
    def validar_crt_cst_csosn(self):
        if self.cst_icms and str(self.cst_icms).strip() and self.csosn and str(self.csosn).strip():
            raise ValueError("CST ICMS e CSOSN não podem estar preenchidos simultaneamente.")
        if self.crt in (1, 2):
            if self.cst_icms and str(self.cst_icms).strip():
                raise ValueError("CRT 1 ou 2 (Simples Nacional) deve usar apenas CSOSN, não CST.")
        elif self.crt == 3:
            if self.csosn and str(self.csosn).strip():
                raise ValueError("CRT 3 (Regime Normal) deve usar apenas CST, não CSOSN.")
        return self


class RegraFiscalIcmsCreate(RegraFiscalIcmsBase):
    empresa_id: int = Field(..., gt=0)


class RegraFiscalIcmsUpdate(BaseModel):
    ativo: Optional[bool] = None
    ordem_prioridade: Optional[int] = Field(None, ge=0, le=9999)
    crt: Optional[int] = Field(None, ge=1, le=3)
    tipo_operacao: Optional[TipoOperacaoEnum] = None
    tipo_destinatario: Optional[TipoDestinatarioEnum] = None
    uf_destinatario: Optional[str] = Field(None, max_length=2)
    ncm_prefix: Optional[str] = Field(None, max_length=4)
    ncm_exato: Optional[str] = Field(None, max_length=8)
    cest: Optional[str] = Field(None, max_length=20)
    cfop_filtro: Optional[str] = Field(None, max_length=4)
    finalidade_emissao: Optional[str] = Field(None, max_length=50)
    consumidor_final: Optional[bool] = None
    contribuinte_icms: Optional[bool] = None
    vigencia_inicio: Optional[date] = None
    vigencia_fim: Optional[date] = None
    observacao_interna: Optional[str] = Field(None, max_length=2000)

    cfop: Optional[str] = Field(None, min_length=4, max_length=4)
    origem_mercadoria: Optional[int] = Field(None, ge=0, le=8)
    cst_icms: Optional[str] = Field(None, max_length=5)
    csosn: Optional[str] = Field(None, max_length=5)
    aliquota_icms: Optional[Decimal] = Field(None, ge=0, le=100)
    modalidade_bc_icms: Optional[str] = Field(None, max_length=2)
    percentual_reducao_bc: Optional[Decimal] = Field(None, ge=0, le=100)
    gera_icms_st: Optional[bool] = None
    aliquota_icms_st: Optional[Decimal] = Field(None, ge=0, le=100)
    modalidade_bc_icms_st: Optional[str] = Field(None, max_length=2)
    percentual_mva_st: Optional[Decimal] = Field(None, ge=0, le=1000)
    permite_credito_icms: Optional[bool] = None

    @model_validator(mode="after")
    def validar_crt_cst_csosn(self):
        cst = self.cst_icms and str(self.cst_icms).strip()
        csosn = self.csosn and str(self.csosn).strip()
        if cst and csosn:
            raise ValueError("CST ICMS e CSOSN não podem estar preenchidos simultaneamente.")
        if self.crt in (1, 2) and cst:
            raise ValueError("CRT 1 ou 2 (Simples Nacional) deve usar apenas CSOSN, não CST.")
        if self.crt == 3 and csosn:
            raise ValueError("CRT 3 (Regime Normal) deve usar apenas CST, não CSOSN.")
        return self


class RegraFiscalIcmsResponse(RegraFiscalIcmsBase):
    id: int
    empresa_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
