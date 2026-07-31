# PDV Ibix — Rastreio imutável de origem comercial da venda
from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.base import BaseModel


class VendaOrigem(BaseModel):
    """Cadeia comercial: origem imediata (pai direto) e raiz (proposta inicial)."""

    __tablename__ = "venda_origens"
    __table_args__ = (
        UniqueConstraint(
            "venda_id",
            "papel",
            "tipo_origem",
            "documento_id",
            name="uq_venda_origens_venda_papel_tipo_doc",
        ),
    )

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    venda_id = Column(Integer, ForeignKey("vendas.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_origem = Column(String(30), nullable=False, comment="manual | orcamento | ordem_servico | pedido")
    documento_id = Column(Integer, nullable=True)
    documento_ref = Column(String(100), nullable=True)
    papel = Column(String(20), nullable=False, comment="imediata | raiz")
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)

    venda = relationship("Venda", foreign_keys=[venda_id])
