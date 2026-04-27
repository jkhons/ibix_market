# PDV Ibix - Modelo FiscalDownloadLog (auditoria de downloads XML/PDF)
import enum
from typing import TYPE_CHECKING

from sqlalchemy import Column, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class DocumentoTipoFiscalEnum(str, enum.Enum):
    """Tipo de documento fiscal"""
    NFSE = "nfse"
    NFE = "nfe"
    NFCE = "nfce"


class ArquivoTipoFiscalEnum(str, enum.Enum):
    """Tipo de arquivo baixado"""
    XML = "xml"
    PDF = "pdf"


class FiscalDownloadLog(BaseModel):
    """Modelo para tabela fiscal_download_log (quem baixou o quê e quando)"""
    __tablename__ = "fiscal_download_log"

    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, comment="Usuário que fez o download")
    documento_tipo = Column(
        Enum(DocumentoTipoFiscalEnum),
        nullable=False,
        comment="Tipo do documento (NFSE, NFE, NFCE)",
    )
    documento_id = Column(Integer, nullable=False, comment="ID da nota na tabela correspondente")
    arquivo_tipo = Column(
        Enum(ArquivoTipoFiscalEnum),
        nullable=False,
        comment="Tipo do arquivo (xml, pdf)",
    )

    usuario = relationship("Usuario", foreign_keys=[usuario_id])

    __table_args__ = (
        Index("idx_fiscal_download_log_usuario", "usuario_id"),
        Index("idx_fiscal_download_log_documento", "documento_tipo", "documento_id"),
        Index("idx_fiscal_download_log_created_at", "created_at"),
        {"comment": "Auditoria de downloads de XML/PDF de documentos fiscais"},
    )

    def __repr__(self):
        return f"<FiscalDownloadLog(id={self.id}, usuario_id={self.usuario_id}, documento_tipo='{self.documento_tipo}', documento_id={self.documento_id})>"
