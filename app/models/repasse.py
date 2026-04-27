# PDV Ibix - Modelo Repasse Financeiro
"""Registro de repasses manuais da plataforma para o CA (modo_recebimento='plataforma')."""
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import Numeric

from ..database.base import BaseModel


class Repasse(BaseModel):
    """Repasse financeiro: transferência da plataforma para o CA."""
    __tablename__ = "repasses"

    cliente_id = Column(
        Integer, ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="CA (cliente) que recebe o repasse",
    )
    valor_bruto = Column(
        Numeric(12, 2), nullable=False,
        comment="Total bruto de vendas pagas no período",
    )
    valor_taxa = Column(
        Numeric(12, 2), nullable=False, default=0,
        comment="Total de taxas da plataforma",
    )
    valor_liquido = Column(
        Numeric(12, 2), nullable=False,
        comment="Valor líquido repassado (bruto - taxa)",
    )
    valor_bruto_produto = Column(
        Numeric(12, 2), nullable=True,
        comment="Parcela do bruto referente a produtos",
    )
    valor_bruto_frete = Column(
        Numeric(12, 2), nullable=True,
        comment="Parcela do bruto referente a frete",
    )
    periodo_inicio = Column(
        Date, nullable=False,
        comment="Início do período coberto pelo repasse",
    )
    periodo_fim = Column(
        Date, nullable=False,
        comment="Fim do período coberto pelo repasse",
    )
    status = Column(
        String(20), nullable=False, server_default="pendente",
        comment="pendente, repassado, cancelado",
    )
    data_repasse = Column(
        DateTime(timezone=True), nullable=True,
        comment="Data/hora em que o repasse foi efetivado",
    )
    comprovante = Column(
        Text, nullable=True,
        comment="URL ou descrição do comprovante de transferência",
    )
    observacao = Column(
        Text, nullable=True,
        comment="Notas do SuperAdmin sobre o repasse",
    )
    usuario_id = Column(
        Integer, ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        comment="Usuário (SuperAdmin) que registrou o repasse",
    )

    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    usuario = relationship("Usuario", foreign_keys=[usuario_id])

    def __repr__(self):
        return f"<Repasse(id={self.id}, cliente_id={self.cliente_id}, status='{self.status}', valor_liquido={self.valor_liquido})>"
