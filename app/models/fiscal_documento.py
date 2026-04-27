# PDV Ibix - Modelos do Mapa Fiscal NF-e (fiscal_documentos, snapshots, itens, totais, transporte, duplicatas, xml_store, eventos)
# Conforme plano: Bloco B — domínio (models, enums, regras de transição).
# Base para numeração por tenant_id + empresa_emitente_id + modelo + serie; emitente = Cliente Administrador.
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

# =========================================================
# ENUMS
# =========================================================


class FiscalTipoDocumento(str, Enum):
    NFE = "NFE"


class FiscalStatusDocumento(str, Enum):
    RASCUNHO = "rascunho"
    PRE_MONTADA = "pre_montada"
    MONTADA = "montada"
    ASSINADA = "assinada"
    TRANSMITIDA = "transmitida"
    AUTORIZADA = "autorizada"
    REJEITADA = "rejeitada"
    CANCELADA = "cancelada"
    DENEGADA = "denegada"
    INUTILIZADA = "inutilizada"


class FiscalAmbiente(int, Enum):
    PRODUCAO = 1
    HOMOLOGACAO = 2


class FiscalTipoOperacao(int, Enum):
    ENTRADA = 0
    SAIDA = 1


class FiscalFinalidadeEmissao(int, Enum):
    NORMAL = 1
    COMPLEMENTAR = 2
    AJUSTE = 3
    DEVOLUCAO = 4


class FiscalTipoXml(str, Enum):
    MONTADO = "montado"
    ASSINADO = "assinado"
    ENVIADO = "enviado"
    RETORNO = "retorno"
    AUTORIZADO = "autorizado"
    CANCELAMENTO = "cancelamento"
    CCE = "cce"


class FiscalTipoEvento(str, Enum):
    AUTORIZACAO = "autorizacao"
    REJEICAO = "rejeicao"
    CANCELAMENTO = "cancelamento"
    CARTA_CORRECAO = "carta_correcao"
    INUTILIZACAO = "inutilizacao"
    CONTINGENCIA = "contingencia"


# =========================================================
# CABEÇALHO
# =========================================================


class FiscalDocumento(Base):
    """Cabeçalho da NF-e (modelo 55). Numeração por tenant_id + empresa_emitente_id + modelo + serie."""
    __tablename__ = "fiscal_documentos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cliente_administrador_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    empresa_emitente_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pedido_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    tipo_documento: Mapped[str] = mapped_column(String(20), nullable=False, default=FiscalTipoDocumento.NFE.value)
    modelo: Mapped[str] = mapped_column(String(2), nullable=False, default="55")
    serie: Mapped[str] = mapped_column(String(3), nullable=False)
    numero: Mapped[int] = mapped_column(BigInteger, nullable=False)

    natureza_operacao: Mapped[str] = mapped_column(String(120), nullable=False)
    finalidade_emissao: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=FiscalFinalidadeEmissao.NORMAL.value)
    tipo_operacao: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    forma_pagamento: Mapped[str | None] = mapped_column(String(2), nullable=True)
    presenca_comprador: Mapped[str | None] = mapped_column(String(2), nullable=True)
    ambiente: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default=FiscalStatusDocumento.RASCUNHO.value)

    chave_acesso: Mapped[str | None] = mapped_column(String(44), nullable=True)
    codigo_numerico: Mapped[str | None] = mapped_column(String(8), nullable=True)
    cuf: Mapped[str] = mapped_column(String(2), nullable=False)
    codigo_municipio_fato_gerador: Mapped[str | None] = mapped_column(String(7), nullable=True)

    data_emissao: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_saida_entrada: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    protocolo_autorizacao: Mapped[str | None] = mapped_column(String(30), nullable=True)
    data_autorizacao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    codigo_status_sefaz: Mapped[str | None] = mapped_column(String(10), nullable=True)
    motivo_status: Mapped[str | None] = mapped_column(Text, nullable=True)

    observacoes_fisco: Mapped[str | None] = mapped_column(Text, nullable=True)
    informacoes_complementares: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    emitente_snapshot: Mapped["FiscalDocumentoEmitenteSnapshot"] = relationship(
        back_populates="documento", uselist=False, cascade="all, delete-orphan"
    )
    destinatario_snapshot: Mapped["FiscalDocumentoDestinatarioSnapshot"] = relationship(
        back_populates="documento", uselist=False, cascade="all, delete-orphan"
    )
    itens: Mapped[list["FiscalDocumentoItem"]] = relationship(
        back_populates="documento", cascade="all, delete-orphan", order_by="FiscalDocumentoItem.ordem"
    )
    totais: Mapped["FiscalDocumentoTotais"] = relationship(
        back_populates="documento", uselist=False, cascade="all, delete-orphan"
    )
    transporte: Mapped["FiscalDocumentoTransporte"] = relationship(
        back_populates="documento", uselist=False, cascade="all, delete-orphan"
    )
    duplicatas: Mapped[list["FiscalDocumentoDuplicata"]] = relationship(
        back_populates="documento", cascade="all, delete-orphan"
    )
    xmls: Mapped[list["FiscalXmlStore"]] = relationship(
        back_populates="documento", cascade="all, delete-orphan"
    )
    eventos: Mapped[list["FiscalEventoDocumento"]] = relationship(
        back_populates="documento", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "empresa_emitente_id", "modelo", "serie", "numero",
            name="uq_fiscal_documento_numero"
        ),
        Index("ix_fiscal_documentos_tenant_status", "tenant_id", "status"),
        Index("ix_fiscal_documentos_pedido", "pedido_id"),
        Index("ix_fiscal_documentos_chave", "chave_acesso"),
    )


# =========================================================
# SNAPSHOT EMITENTE
# =========================================================


class FiscalDocumentoEmitenteSnapshot(Base):
    __tablename__ = "fiscal_documento_emitente_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fiscal_documento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("fiscal_documentos.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    razao_social: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cnpj: Mapped[str] = mapped_column(String(14), nullable=False)
    ie: Mapped[str | None] = mapped_column(String(20), nullable=True)
    im: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cnae: Mapped[str | None] = mapped_column(String(10), nullable=True)
    crt: Mapped[str] = mapped_column(String(1), nullable=False)
    crt_descricao: Mapped[str | None] = mapped_column(String(80), nullable=True)

    logradouro: Mapped[str] = mapped_column(String(255), nullable=False)
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    complemento: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bairro: Mapped[str] = mapped_column(String(120), nullable=False)
    codigo_municipio_ibge: Mapped[str] = mapped_column(String(7), nullable=False)
    municipio: Mapped[str] = mapped_column(String(120), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    cep: Mapped[str] = mapped_column(String(8), nullable=False)
    codigo_pais: Mapped[str] = mapped_column(String(4), nullable=False, default="1058")
    pais: Mapped[str] = mapped_column(String(60), nullable=False, default="BRASIL")
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    documento: Mapped["FiscalDocumento"] = relationship(back_populates="emitente_snapshot")


# =========================================================
# SNAPSHOT DESTINATÁRIO
# =========================================================


class FiscalDocumentoDestinatarioSnapshot(Base):
    __tablename__ = "fiscal_documento_destinatario_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fiscal_documento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("fiscal_documentos.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    tipo_pessoa: Mapped[str] = mapped_column(String(10), nullable=False)
    nome_razao_social: Mapped[str] = mapped_column(String(255), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(11), nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    ie: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ind_ie_dest: Mapped[str | None] = mapped_column(String(1), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    logradouro: Mapped[str] = mapped_column(String(255), nullable=False)
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    complemento: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bairro: Mapped[str] = mapped_column(String(120), nullable=False)
    codigo_municipio_ibge: Mapped[str] = mapped_column(String(7), nullable=False)
    municipio: Mapped[str] = mapped_column(String(120), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    cep: Mapped[str] = mapped_column(String(8), nullable=False)
    codigo_pais: Mapped[str] = mapped_column(String(4), nullable=False, default="1058")
    pais: Mapped[str] = mapped_column(String(60), nullable=False, default="BRASIL")
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    documento: Mapped["FiscalDocumento"] = relationship(back_populates="destinatario_snapshot")


# =========================================================
# ITENS
# =========================================================


class FiscalDocumentoItem(Base):
    __tablename__ = "fiscal_documento_itens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fiscal_documento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("fiscal_documentos.id", ondelete="CASCADE"), nullable=False
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)

    produto_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pedido_item_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    codigo_produto: Mapped[str] = mapped_column(String(60), nullable=False)
    ean: Mapped[str | None] = mapped_column(String(14), nullable=True)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    ncm: Mapped[str] = mapped_column(String(8), nullable=False)
    cest: Mapped[str | None] = mapped_column(String(7), nullable=True)
    extipi: Mapped[str | None] = mapped_column(String(3), nullable=True)
    cfop: Mapped[str] = mapped_column(String(4), nullable=False)

    unidade_comercial: Mapped[str] = mapped_column(String(6), nullable=False)
    quantidade_comercial: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    valor_unitario_comercial: Mapped[Decimal] = mapped_column(Numeric(15, 10), nullable=False)
    valor_bruto: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    ean_tributavel: Mapped[str | None] = mapped_column(String(14), nullable=True)
    unidade_tributavel: Mapped[str] = mapped_column(String(6), nullable=False)
    quantidade_tributavel: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    valor_unitario_tributavel: Mapped[Decimal] = mapped_column(Numeric(15, 10), nullable=False)

    valor_frete: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_seguro: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_desconto: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_outras_despesas: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    indicador_total: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)

    documento: Mapped["FiscalDocumento"] = relationship(back_populates="itens")
    impostos: Mapped["FiscalDocumentoItemImpostos"] = relationship(
        back_populates="item", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("fiscal_documento_id", "ordem", name="uq_fiscal_documento_item_ordem"),
    )


class FiscalDocumentoItemImpostos(Base):
    __tablename__ = "fiscal_documento_item_impostos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fiscal_documento_item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("fiscal_documento_itens.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    origem_mercadoria: Mapped[str] = mapped_column(String(1), nullable=False)
    cst_icms: Mapped[str | None] = mapped_column(String(3), nullable=True)
    csosn: Mapped[str | None] = mapped_column(String(3), nullable=True)
    modalidade_bc_icms: Mapped[str | None] = mapped_column(String(1), nullable=True)
    base_icms: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    aliquota_icms: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False, default=Decimal("0.0000"))
    valor_icms: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))

    modalidade_bc_icms_st: Mapped[str | None] = mapped_column(String(1), nullable=True)
    base_icms_st: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    aliquota_icms_st: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False, default=Decimal("0.0000"))
    valor_icms_st: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))

    base_fcp: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    aliquota_fcp: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False, default=Decimal("0.0000"))
    valor_fcp: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))

    base_ipi: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    aliquota_ipi: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False, default=Decimal("0.0000"))
    valor_ipi: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    cst_ipi: Mapped[str | None] = mapped_column(String(2), nullable=True)

    base_pis: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    aliquota_pis: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False, default=Decimal("0.0000"))
    valor_pis: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    cst_pis: Mapped[str | None] = mapped_column(String(2), nullable=True)

    base_cofins: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    aliquota_cofins: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False, default=Decimal("0.0000"))
    valor_cofins: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    cst_cofins: Mapped[str | None] = mapped_column(String(2), nullable=True)

    valor_aprox_tributos: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))

    item: Mapped["FiscalDocumentoItem"] = relationship(back_populates="impostos")


# =========================================================
# TOTAIS
# =========================================================


class FiscalDocumentoTotais(Base):
    __tablename__ = "fiscal_documento_totais"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fiscal_documento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("fiscal_documentos.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    base_icms: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_icms: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    base_icms_st: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_icms_st: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_fcp: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_produtos: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_frete: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_seguro: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_desconto: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_ii: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_ipi: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_ipi_devolvido: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_pis: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_cofins: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    outras_despesas: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_total_nota: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    valor_total_tributos_aprox: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))

    documento: Mapped["FiscalDocumento"] = relationship(back_populates="totais")


# =========================================================
# TRANSPORTE
# =========================================================


class FiscalDocumentoTransporte(Base):
    __tablename__ = "fiscal_documento_transporte"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fiscal_documento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("fiscal_documentos.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    modalidade_frete: Mapped[str] = mapped_column(String(1), nullable=False, default="9")
    transportadora_nome: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transportadora_cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    transportadora_cpf: Mapped[str | None] = mapped_column(String(11), nullable=True)
    transportadora_ie: Mapped[str | None] = mapped_column(String(20), nullable=True)
    transportadora_endereco: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transportadora_municipio: Mapped[str | None] = mapped_column(String(120), nullable=True)
    transportadora_uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    codigo_antt: Mapped[str | None] = mapped_column(String(20), nullable=True)
    placa_veiculo: Mapped[str | None] = mapped_column(String(8), nullable=True)
    uf_veiculo: Mapped[str | None] = mapped_column(String(2), nullable=True)
    quantidade_volumes: Mapped[Decimal | None] = mapped_column(Numeric(15, 3), nullable=True)
    especie: Mapped[str | None] = mapped_column(String(60), nullable=True)
    marca: Mapped[str | None] = mapped_column(String(60), nullable=True)
    numeracao: Mapped[str | None] = mapped_column(String(60), nullable=True)
    peso_bruto: Mapped[Decimal | None] = mapped_column(Numeric(15, 3), nullable=True)
    peso_liquido: Mapped[Decimal | None] = mapped_column(Numeric(15, 3), nullable=True)

    documento: Mapped["FiscalDocumento"] = relationship(back_populates="transporte")


# =========================================================
# DUPLICATAS
# =========================================================


class FiscalDocumentoDuplicata(Base):
    __tablename__ = "fiscal_documento_duplicatas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fiscal_documento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("fiscal_documentos.id", ondelete="CASCADE"), nullable=False
    )
    numero: Mapped[str] = mapped_column(String(20), nullable=False)
    data_vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    documento: Mapped["FiscalDocumento"] = relationship(back_populates="duplicatas")


# =========================================================
# XML STORE
# =========================================================


class FiscalXmlStore(Base):
    __tablename__ = "fiscal_xml_store"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fiscal_documento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("fiscal_documentos.id", ondelete="CASCADE"), nullable=False
    )
    tipo_xml: Mapped[str] = mapped_column(String(20), nullable=False)
    versao_layout: Mapped[str] = mapped_column(String(10), nullable=False)
    ambiente: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    conteudo_xml: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    documento: Mapped["FiscalDocumento"] = relationship(back_populates="xmls")

    __table_args__ = (
        Index("ix_fiscal_xml_store_documento_tipo", "fiscal_documento_id", "tipo_xml"),
    )


# =========================================================
# EVENTOS (documento fiscal_documentos — não confundir com fiscal_evento do legado)
# =========================================================


class FiscalEventoDocumento(Base):
    """Eventos da vida do documento (fiscal_documentos): autorização, rejeição, cancelamento, CCe, inutilização."""
    __tablename__ = "fiscal_eventos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fiscal_documento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("fiscal_documentos.id", ondelete="CASCADE"), nullable=False
    )
    tipo_evento: Mapped[str] = mapped_column(String(30), nullable=False)
    codigo_status: Mapped[str | None] = mapped_column(String(10), nullable=True)
    descricao_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    protocolo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    xml_evento_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fiscal_xml_store.id"), nullable=True)
    xml_retorno_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fiscal_xml_store.id"), nullable=True)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    criado_por_usuario_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    documento: Mapped["FiscalDocumento"] = relationship(back_populates="eventos")

    __table_args__ = (
        Index("ix_fiscal_eventos_documento", "fiscal_documento_id", "ocorrido_em"),
    )


# =========================================================
# REGRAS DE DOMÍNIO
# =========================================================

STATUS_TRANSITIONS: dict[str, set[str]] = {
    FiscalStatusDocumento.RASCUNHO.value: {
        FiscalStatusDocumento.PRE_MONTADA.value,
        FiscalStatusDocumento.INUTILIZADA.value,
    },
    FiscalStatusDocumento.PRE_MONTADA.value: {
        FiscalStatusDocumento.MONTADA.value,
        FiscalStatusDocumento.REJEITADA.value,
    },
    FiscalStatusDocumento.MONTADA.value: {
        FiscalStatusDocumento.ASSINADA.value,
        FiscalStatusDocumento.REJEITADA.value,
    },
    FiscalStatusDocumento.ASSINADA.value: {
        FiscalStatusDocumento.TRANSMITIDA.value,
        FiscalStatusDocumento.REJEITADA.value,
    },
    FiscalStatusDocumento.TRANSMITIDA.value: {
        FiscalStatusDocumento.AUTORIZADA.value,
        FiscalStatusDocumento.REJEITADA.value,
        FiscalStatusDocumento.DENEGADA.value,
    },
    FiscalStatusDocumento.REJEITADA.value: {
        FiscalStatusDocumento.PRE_MONTADA.value,
        FiscalStatusDocumento.INUTILIZADA.value,
    },
    FiscalStatusDocumento.AUTORIZADA.value: {
        FiscalStatusDocumento.CANCELADA.value,
    },
    FiscalStatusDocumento.CANCELADA.value: set(),
    FiscalStatusDocumento.DENEGADA.value: set(),
    FiscalStatusDocumento.INUTILIZADA.value: set(),
}


def validar_transicao_status(status_atual: str, novo_status: str) -> bool:
    return novo_status in STATUS_TRANSITIONS.get(status_atual, set())


def exigir_emitente_cliente_administrador(documento: FiscalDocumento) -> None:
    if documento.empresa_emitente_id != documento.cliente_administrador_id:
        raise ValueError(
            "Regra fiscal violada: o emitente fiscal deve ser sempre o Cliente Administrador."
        )


def documento_esta_congelado(status: str) -> bool:
    return status in {
        FiscalStatusDocumento.AUTORIZADA.value,
        FiscalStatusDocumento.CANCELADA.value,
        FiscalStatusDocumento.DENEGADA.value,
        FiscalStatusDocumento.INUTILIZADA.value,
    }
