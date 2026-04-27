# PDV Ibix - Modelo NFeTentativaEnvio (auditoria de tentativas de envio NF-e à SEFAZ)
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class NFeTentativaEnvio(BaseModel):
    """
    Registro de cada tentativa de envio de NF-e (autorização/cancelamento).
    Usado para auditoria, diagnóstico e idempotência (evitar reenvio quando já autorizada).
    """
    __tablename__ = "nfe_tentativa_envio"

    nota_fiscal_id = Column(Integer, ForeignKey("notas_fiscais.id", ondelete="CASCADE"), nullable=False, index=True, comment="Nota fiscal enviada")
    empresa_id = Column(Integer, ForeignKey("empresa.id", ondelete="CASCADE"), nullable=False, index=True, comment="Empresa emissora")

    sucesso = Column(Boolean, nullable=False, default=False, comment="True se autorizado/evento aceito")
    status_http = Column(Integer, nullable=True, comment="Código HTTP da resposta (200, 400, 403, etc.)")
    http_content_type = Column(String(100), nullable=True, comment="Content-Type do retorno (text/html, application/xml, etc.)")

    tipo_erro = Column(String(50), nullable=True, comment="validacao, assinatura, ssl, soap_fault, http_html, rejeicao_fiscal, timeout, conexao")
    servico = Column(String(30), nullable=False, comment="autorizacao, cancelamento, consulta_recibo, inutilizacao")
    ambiente_sefaz = Column(String(20), nullable=True, comment="homologacao ou producao (nomenclatura SEFAZ)")
    mensagem = Column(Text, nullable=True, comment="Mensagem de erro ou retorno (cStat/xMotivo)")

    cert_serial = Column(String(80), nullable=True, comment="Serial do certificado A1 usado")
    cert_subject = Column(String(255), nullable=True, comment="Subject do certificado (truncado)")
    xml_hash_sha256 = Column(String(64), nullable=True, comment="SHA-256 do XML assinado enviado")
    tentativa_numero = Column(Integer, nullable=False, default=1, comment="Número da tentativa para esta nota (1, 2, 3...)")
    duracao_ms = Column(Integer, nullable=True, comment="Duração da chamada em milissegundos")

    resposta_bruta = Column(Text, nullable=True, comment="Resposta bruta SEFAZ (completa até limite do campo)")
    resposta_bruta_path = Column(String(500), nullable=True, comment="Path do XML de retorno quando excede limite")
    payload_retorno = Column(Text, nullable=True, comment="JSON do retorno parseado (protocolo, chave, etc.)")

    cstat = Column(String(10), nullable=True, comment="cStat SEFAZ (protNFe.infProt ou retEnviNFe)")
    xmotivo = Column(Text, nullable=True, comment="xMotivo SEFAZ")
    nrec = Column(String(20), nullable=True, comment="nRec (recibo) quando lote 103")
    protocolo = Column(String(50), nullable=True, comment="Protocolo nProt")
    url = Column(String(255), nullable=True, comment="URL do webservice SEFAZ")
    erro_tecnico = Column(Text, nullable=True, comment="Exceção técnica (timeout, SSL, etc.)")
    tipo_resultado = Column(
        String(30),
        nullable=True,
        comment="erro_tecnico, lote_recebido, lote_processado, autorizada, rejeitada, resposta_invalida, resposta_vazia",
    )

    __table_args__ = (
        Index("ix_nfe_tentativa_nota_empresa", "nota_fiscal_id", "empresa_id"),
        Index("ix_nfe_tentativa_created", "created_at"),
        {"comment": "Auditoria de tentativas de envio NF-e à SEFAZ"},
    )

    nota_fiscal = relationship("NotaFiscal", backref="tentativas_envio_nfe")
    empresa = relationship("Empresa", backref="tentativas_envio_nfe")
