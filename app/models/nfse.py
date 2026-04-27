# PDV Ibix - Modelos do módulo NFS-e (conforme MODULO_FATURAMENT_V2.MD Parte V)
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class NfseInvoice(BaseModel):
    """Documento universal NFS-e: origem (SUBSCRIPTION/OS/MANUAL) -> emissor -> tomador -> retorno."""
    __tablename__ = "nfse_invoices"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="RESTRICT"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True)

    origin_type = Column(String(20), nullable=False)  # SUBSCRIPTION | OS | MANUAL
    origin_id = Column(Integer, nullable=True)

    municipio_prestacao_ibge = Column(Integer, nullable=False)
    data_competencia = Column(Date, nullable=False)

    descricao_servico = Column(Text, nullable=True)
    item_lista_servico = Column(String(20), nullable=True)
    cnae = Column(String(20), nullable=True)

    valor_servicos = Column(Numeric(15, 2), nullable=False, default=0)
    valor_deducoes = Column(Numeric(15, 2), nullable=False, default=0)
    base_iss = Column(Numeric(15, 2), nullable=False, default=0)
    aliquota_iss = Column(Numeric(9, 4), nullable=False, default=0)
    valor_iss = Column(Numeric(15, 2), nullable=False, default=0)
    iss_retido = Column(Boolean, nullable=False, default=False)
    valor_iss_retido = Column(Numeric(15, 2), nullable=False, default=0)

    status = Column(String(20), nullable=False, default="DRAFT", index=True)  # DRAFT|QUEUED|SENT|AUTHORIZED|REJECTED|CANCELED
    provider = Column(String(20), nullable=False, default="NACIONAL")

    external_id = Column(String(120), nullable=True)
    numero_nfse = Column(String(60), nullable=True)
    codigo_verificacao = Column(String(80), nullable=True)
    url_consulta = Column(String(500), nullable=True)
    data_emissao = Column(DateTime(timezone=True), nullable=True)

    last_error_code = Column(String(40), nullable=True)
    last_error_msg = Column(Text, nullable=True)

    tenant = relationship("Tenant", backref="nfse_invoices", foreign_keys=[tenant_id])
    empresa = relationship("Empresa", backref="nfse_invoices", foreign_keys=[empresa_id])
    cliente = relationship("Cliente", backref="nfse_invoices", foreign_keys=[cliente_id])
    rps_list = relationship("NfseRps", back_populates="nfse_invoice", foreign_keys="NfseRps.nfse_invoice_id")
    message_logs = relationship("NfseMessageLog", back_populates="nfse_invoice", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_nfse_origin", "tenant_id", "origin_type", "origin_id", unique=True),
        Index("ix_nfse_invoices_tenant_empresa_status", "tenant_id", "empresa_id", "status"),
        Index("ix_nfse_invoices_tenant_numero", "tenant_id", "numero_nfse"),
        {"comment": "Notas NFS-e (documento universal por origem)"},
    )


class NfseRps(BaseModel):
    """Numeração e controle de RPS por emissor."""
    __tablename__ = "nfse_rps"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)
    nfse_invoice_id = Column(Integer, ForeignKey("nfse_invoices.id", ondelete="SET NULL"), nullable=True, index=True)

    serie = Column(String(10), nullable=False, default="1")
    numero = Column(BigInteger, nullable=False)
    tipo = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="RESERVED")  # RESERVED | USED | VOID

    nfse_invoice = relationship("NfseInvoice", back_populates="rps_list", foreign_keys=[nfse_invoice_id])

    __table_args__ = (
        Index("uq_nfse_rps", "tenant_id", "empresa_id", "serie", "numero", unique=True),
        Index("ix_nfse_rps_tenant_empresa_status", "tenant_id", "empresa_id", "status"),
        {"comment": "RPS por emissor (controle de numeração)"},
    )


class NfseCredential(BaseModel):
    """Certificado A1 por empresa (opcional; pode usar empresa.certificado_* no MVP)."""
    __tablename__ = "nfse_credentials"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)

    type = Column(String(20), nullable=False, default="A1_PFX")
    pfx_blob = Column(LargeBinary, nullable=False)
    pfx_password = Column(LargeBinary, nullable=False)
    cert_serial = Column(String(80), nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE | EXPIRED | REVOKED

    __table_args__ = (
        Index("ix_nfse_credentials_tenant_empresa_status", "tenant_id", "empresa_id", "status"),
        {"comment": "Credenciais A1 por empresa (NFS-e)"},
    )


class NfseMessageLog(BaseModel):
    """Request/response redigido para auditoria."""
    __tablename__ = "nfse_message_logs"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nfse_invoice_id = Column(Integer, ForeignKey("nfse_invoices.id", ondelete="CASCADE"), nullable=False, index=True)

    direction = Column(String(10), nullable=False)  # OUT | IN
    http_status = Column(Integer, nullable=True)
    payload_redacted = Column(Text, nullable=True)
    response_redacted = Column(Text, nullable=True)

    nfse_invoice = relationship("NfseInvoice", back_populates="message_logs", foreign_keys=[nfse_invoice_id])

    __table_args__ = (
        Index("ix_nfse_message_logs_invoice_created", "tenant_id", "nfse_invoice_id", "created_at"),
        {"comment": "Log de mensagens NFS-e (redigido)"},
    )


class NfseProviderConfig(BaseModel):
    """Parametrização por empresa/município (provider, ambiente)."""
    __tablename__ = "nfse_provider_configs"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True)

    provider = Column(String(20), nullable=False, default="NACIONAL")
    municipio_ibge = Column(Integer, nullable=True)
    environment = Column(String(20), nullable=False, default="HOMOLOG")  # HOMOLOG | PROD
    config_json = Column(JSON, nullable=False)  # JSON/JSONB: parametrização do provider

    __table_args__ = (
        Index("ix_nfse_provider_configs_lookup", "tenant_id", "empresa_id", "provider", "municipio_ibge"),
        {"comment": "Config do provider NFS-e por empresa/município"},
    )
