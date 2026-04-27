# PDV Ibix - Regra Fiscal ICMS (motor tributário NF-e)
"""Modelo para regras fiscais parametrizadas de ICMS. Usado pelo motor tributário para decidir CFOP, CST/CSOSN, origem e alíquotas por item da NF-e."""
from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.base import BaseModel


class TipoOperacaoFiscalEnum(str, enum.Enum):
    """Tipo de operação fiscal (venda interna/interestadual, com ou sem ST)."""
    VENDA_INTERNA = "venda_interna"
    VENDA_INTERESTADUAL = "venda_interestadual"
    VENDA_INTERNA_ST = "venda_interna_st"
    VENDA_INTERESTADUAL_ST = "venda_interestadual_st"
    QUALQUER = "qualquer"


class TipoDestinatarioFiscalEnum(str, enum.Enum):
    """Tipo de destinatário (PF, PJ ou qualquer)."""
    PF = "pf"
    PJ = "pj"
    QUALQUER = "qualquer"


class RegraFiscalIcms(BaseModel):
    """Regra fiscal de ICMS para motor tributário. Vinculada por empresa_id."""
    __tablename__ = "regras_fiscais_icms"

    # Vínculo
    empresa_id = Column(
        Integer,
        ForeignKey("empresa.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Empresa (emitente) a que a regra se aplica",
    )

    # Controle
    ativo = Column(Boolean, nullable=False, default=True)
    ordem_prioridade = Column(Integer, nullable=False, default=100)

    # Campos de filtro (null = qualquer)
    crt = Column(Integer, nullable=True, comment="1 ou 2 = Simples; 3 = Regime Normal")
    tipo_operacao = Column(
        Enum(TipoOperacaoFiscalEnum, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    tipo_destinatario = Column(
        Enum(TipoDestinatarioFiscalEnum, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    uf_destinatario = Column(String(2), nullable=True)
    ncm_prefix = Column(String(4), nullable=True)
    ncm_exato = Column(String(8), nullable=True)
    cest = Column(String(20), nullable=True)
    cfop_filtro = Column(String(4), nullable=True)
    finalidade_emissao = Column(String(50), nullable=True)
    consumidor_final = Column(Boolean, nullable=True)
    contribuinte_icms = Column(Boolean, nullable=True)
    vigencia_inicio = Column(Date, nullable=True)
    vigencia_fim = Column(Date, nullable=True)
    observacao_interna = Column(Text, nullable=True)

    # Campos de resultado (obrigatórios conforme CRT)
    cfop = Column(String(4), nullable=False, comment="CFOP resultante da decisão")
    origem_mercadoria = Column(Integer, nullable=False, comment="Origem 0-8")
    cst_icms = Column(String(5), nullable=True, comment="CST ICMS (apenas CRT 3)")
    csosn = Column(String(5), nullable=True, comment="CSOSN (apenas CRT 1/2)")
    aliquota_icms = Column(Numeric(7, 4), nullable=False, default=0)
    modalidade_bc_icms = Column(String(2), nullable=True)
    percentual_reducao_bc = Column(Numeric(7, 4), nullable=True)
    gera_icms_st = Column(Boolean, nullable=False, default=False)
    aliquota_icms_st = Column(Numeric(7, 4), nullable=True)
    modalidade_bc_icms_st = Column(String(2), nullable=True)
    percentual_mva_st = Column(Numeric(7, 4), nullable=True)
    permite_credito_icms = Column(Boolean, nullable=True)

    # Relacionamentos
    empresa = relationship("Empresa", backref="regras_fiscais_icms")

    __table_args__ = (
        Index("idx_regra_empresa", "empresa_id"),
        Index("idx_regra_prioridade", "empresa_id", "ativo", "ordem_prioridade"),
        Index("idx_regra_ncm", "empresa_id", "ncm_exato", "ncm_prefix"),
    )

    def __repr__(self):
        return f"<RegraFiscalIcms(id={self.id}, empresa_id={self.empresa_id}, cfop={self.cfop})>"
