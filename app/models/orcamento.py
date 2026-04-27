# PDV Ibix - Modelo Orçamento (Módulo Orçamento e Pedido)
from typing import TYPE_CHECKING

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class Orcamento(BaseModel):
    """Orçamento: proposta comercial temporária; não movimenta estoque nem financeiro."""
    __tablename__ = "orcamentos"

    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False, index=True, comment="Estabelecimento que emite")
    vendedor_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    destinatario_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True, index=True, comment="Cliente final/destinatário")
    numero_orcamento = Column(String(50), nullable=False)
    data_validade = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, default="rascunho")  # rascunho, emitido, aprovado, rejeitado, convertido, expirado, cancelado
    subtotal = Column(Numeric(15, 2), nullable=True)
    desconto = Column(Numeric(15, 2), nullable=True)
    acrescimo = Column(Numeric(15, 2), nullable=True)
    total = Column(Numeric(15, 2), nullable=True)
    observacoes = Column(Text, nullable=True)
    condicoes_pagamento = Column(Text, nullable=True)
    convertido_em_pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="SET NULL"), nullable=True, index=True)
    data_conversao = Column(DateTime(timezone=True), nullable=True)

    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    destinatario = relationship("Cliente", foreign_keys=[destinatario_id])
    vendedor = relationship("Usuario", foreign_keys=[vendedor_id])
    convertido_em_pedido = relationship(
        "Pedido",
        foreign_keys=[convertido_em_pedido_id],
        uselist=False,
        viewonly=True,
    )
    itens = relationship("OrcamentoItem", back_populates="orcamento", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Orcamento(id={self.id}, numero='{self.numero_orcamento}', status='{self.status}')>"


class OrcamentoItem(BaseModel):
    """Item do orçamento (snapshot de produto e valores)."""
    __tablename__ = "orcamento_itens"

    orcamento_id = Column(Integer, ForeignKey("orcamentos.id", ondelete="CASCADE"), nullable=False, index=True)
    produto_cliente_id = Column(Integer, ForeignKey("produtos_cliente.id", ondelete="RESTRICT"), nullable=False, index=True)
    codigo_produto = Column(String(50), nullable=True)
    descricao_produto = Column(String(255), nullable=True)
    quantidade = Column(Numeric(15, 3), nullable=False)
    preco_unitario = Column(Numeric(15, 2), nullable=False)
    desconto_percentual = Column(Numeric(5, 2), nullable=True)
    desconto_valor = Column(Numeric(15, 2), nullable=True)
    total_item = Column(Numeric(15, 2), nullable=False)
    observacao_item = Column(Text, nullable=True)

    orcamento = relationship("Orcamento", back_populates="itens")
    produto_cliente = relationship("ProdutoCliente", foreign_keys=[produto_cliente_id])

    def __repr__(self):
        return f"<OrcamentoItem(id={self.id}, orcamento_id={self.orcamento_id}, qtd={self.quantidade})>"
