# PDV Ibix - Estabelecimento Fiscal (Fase 3.1.1)
"""Configuração fiscal por estabelecimento (cliente_id). Emissão vinculada ao estabelecimento."""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class EstabelecimentoFiscal(BaseModel):
    """Estabelecimento fiscal: CNPJ, IE, CRT, certificado, regime, série NF-e, alíquotas por UF."""
    __tablename__ = "estabelecimentos_fiscais"

    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Estabelecimento (clientes.id)",
    )
    cnpj = Column(String(18), nullable=False)
    ie = Column(String(20), nullable=True)
    crt = Column(Integer, nullable=True, comment="1=Simples, 2=Simples excesso, 3=Regime normal")
    certificado_digital_path = Column(String(512), nullable=True)
    regime_tributario = Column(String(50), nullable=True)
    serie_nfe = Column(String(10), nullable=True, default="1")
    aliquotas_uf = Column(Text, nullable=True, comment="JSON: alíquotas por UF")
    ativo = Column(Boolean, nullable=False, default=True)

    cliente = relationship("Cliente", foreign_keys=[cliente_id])

    def __repr__(self):
        return f"<EstabelecimentoFiscal(id={self.id}, cliente_id={self.cliente_id}, cnpj='{self.cnpj}')>"
