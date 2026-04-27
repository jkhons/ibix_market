# PDV Ibix - Modelo FiscalEvento (histórico de eventos do provedor fiscal)
import enum
from typing import TYPE_CHECKING

from sqlalchemy import Column, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class DocumentoTipoFiscalEnum(str, enum.Enum):
    """Tipo de documento fiscal"""
    NFSE = "nfse"
    NFE = "nfe"
    NFCE = "nfce"


class EventoFiscalEnum(str, enum.Enum):
    """Tipo de evento fiscal"""
    ENVIO = "envio"
    RETORNO = "retorno"
    REJEICAO = "rejeicao"
    AUTORIZACAO = "autorizacao"
    CANCELAMENTO = "cancelamento"


class FiscalEvento(BaseModel):
    """Modelo para tabela fiscal_evento (histórico de eventos do provedor)"""
    __tablename__ = "fiscal_evento"

    documento_tipo = Column(
        Enum(DocumentoTipoFiscalEnum),
        nullable=False,
        comment="Tipo do documento (NFSE, NFE, NFCE)",
    )
    documento_id = Column(Integer, nullable=False, comment="ID da nota na tabela correspondente (notas_servico.id ou notas_fiscais.id)")
    empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, comment="ID da empresa emissora")
    evento = Column(
        Enum(EventoFiscalEnum),
        nullable=False,
        comment="Tipo do evento (envio, retorno, rejeição, autorização, cancelamento)",
    )
    payload_raw = Column(Text, nullable=True, comment="Payload raw retornado pelo provedor (JSON)")
    resposta_bruta = Column(Text, nullable=True, comment="Resposta bruta do webservice (ex.: SEFAZ)")
    http_content_type = Column(String(100), nullable=True, comment="Content-Type do retorno HTTP")
    status_http = Column(Integer, nullable=True, comment="Código HTTP do retorno (ex.: 200, 400)")
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, comment="Usuário que disparou o evento")

    empresa = relationship("Empresa", back_populates="fiscal_eventos")
    usuario = relationship("Usuario", foreign_keys=[usuario_id])

    __table_args__ = (
        Index("idx_fiscal_evento_documento", "documento_tipo", "documento_id"),
        Index("idx_fiscal_evento_empresa", "empresa_id"),
        Index("idx_fiscal_evento_evento", "evento"),
        Index("idx_fiscal_evento_created_at", "created_at"),
        {"comment": "Histórico de eventos fiscais (envio, retorno, rejeição, autorização, cancelamento)"},
    )

    def __repr__(self):
        return f"<FiscalEvento(id={self.id}, documento_tipo='{self.documento_tipo}', evento='{self.evento}')>"
