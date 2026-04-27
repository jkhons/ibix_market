# PDV Ibix - Modelo Pedido (Módulo Orçamento e Pedido)
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class Pedido(BaseModel):
    """Pedido: compromisso de venda; pode reservar estoque e gerar NF."""
    __tablename__ = "pedidos"

    orcamento_id = Column(Integer, ForeignKey("orcamentos.id", ondelete="SET NULL"), nullable=True, index=True)
    venda_id = Column(Integer, ForeignKey("vendas.id", ondelete="SET NULL"), nullable=True, index=True, comment="Quando pedido nasce de venda no PDV")
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False, index=True)
    vendedor_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    numero_pedido = Column(String(50), nullable=False)
    data_pedido = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    data_prevista_entrega = Column(Date, nullable=True)
    status = Column(String(30), nullable=False, default="rascunho")  # rascunho, liberado, bloqueado, em_separacao, faturado_parcial, faturado_total, cancelado
    reserva_estoque = Column(Boolean, nullable=False, default=False)
    data_reserva = Column(DateTime(timezone=True), nullable=True)
    subtotal = Column(Numeric(15, 2), nullable=True)
    desconto = Column(Numeric(15, 2), nullable=True)
    acrescimo = Column(Numeric(15, 2), nullable=True)
    total = Column(Numeric(15, 2), nullable=True)
    observacoes = Column(Text, nullable=True)

    orcamento = relationship(
        "Orcamento",
        foreign_keys=[orcamento_id],
        uselist=False,
    )
    venda = relationship("Venda", foreign_keys=[venda_id])
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    vendedor = relationship("Usuario", foreign_keys=[vendedor_id])
    itens = relationship("PedidoItem", back_populates="pedido", cascade="all, delete-orphan")
    faturamentos = relationship("PedidoFaturamento", back_populates="pedido", cascade="all, delete-orphan")
    historico = relationship("PedidoHistorico", back_populates="pedido", cascade="all, delete-orphan")
    reservas = relationship("ReservaEstoque", back_populates="pedido", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Pedido(id={self.id}, numero='{self.numero_pedido}', status='{self.status}')>"


class PedidoItem(BaseModel):
    """Item do pedido (snapshot + quantidade_faturada para faturamento parcial)."""
    __tablename__ = "pedido_itens"

    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False, index=True)
    produto_cliente_id = Column(Integer, ForeignKey("produtos_cliente.id", ondelete="RESTRICT"), nullable=False, index=True)
    codigo_produto = Column(String(50), nullable=True)
    descricao_produto = Column(String(255), nullable=True)
    quantidade = Column(Numeric(15, 3), nullable=False)
    quantidade_faturada = Column(Numeric(15, 3), nullable=False, default=0)
    preco_unitario = Column(Numeric(15, 2), nullable=False)
    desconto_percentual = Column(Numeric(5, 2), nullable=True)
    desconto_valor = Column(Numeric(15, 2), nullable=True)
    total_item = Column(Numeric(15, 2), nullable=False)
    status = Column(String(20), nullable=False, default="pendente")  # pendente, parcial, faturado, cancelado

    pedido = relationship("Pedido", back_populates="itens")
    produto_cliente = relationship("ProdutoCliente", foreign_keys=[produto_cliente_id])

    def __repr__(self):
        return f"<PedidoItem(id={self.id}, pedido_id={self.pedido_id}, qtd={self.quantidade})>"


class PedidoFaturamento(BaseModel):
    """Ligação pedido ↔ nota fiscal (faturamento total ou parcial)."""
    __tablename__ = "pedido_faturamento"

    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False, index=True)
    nota_fiscal_id = Column(Integer, ForeignKey("notas_fiscais.id", ondelete="RESTRICT"), nullable=False, index=True)
    data_faturamento = Column(DateTime(timezone=True), nullable=True)
    valor_faturado = Column(Numeric(15, 2), nullable=True)

    pedido = relationship("Pedido", back_populates="faturamentos")
    nota_fiscal = relationship("NotaFiscal", foreign_keys=[nota_fiscal_id])

    def __repr__(self):
        return f"<PedidoFaturamento(id={self.id}, pedido_id={self.pedido_id}, nota_fiscal_id={self.nota_fiscal_id})>"


class PedidoHistorico(BaseModel):
    """Histórico de mudança de status do pedido."""
    __tablename__ = "pedido_historico"

    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False, index=True)
    status_anterior = Column(String(50), nullable=True)
    status_novo = Column(String(50), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    observacao = Column(Text, nullable=True)
    data_mudanca = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    pedido = relationship("Pedido", back_populates="historico")
    usuario = relationship("Usuario", foreign_keys=[usuario_id])

    def __repr__(self):
        return f"<PedidoHistorico(id={self.id}, pedido_id={self.pedido_id}, {self.status_anterior}->{self.status_novo})>"


class ReservaEstoque(BaseModel):
    """Reserva de quantidade por produto para um pedido (opcional)."""
    __tablename__ = "reserva_estoque"

    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False, index=True)
    produto_cliente_id = Column(Integer, ForeignKey("produtos_cliente.id", ondelete="CASCADE"), nullable=False, index=True)
    quantidade_reservada = Column(Numeric(15, 3), nullable=False)

    pedido = relationship("Pedido", back_populates="reservas")
    produto_cliente = relationship("ProdutoCliente", foreign_keys=[produto_cliente_id])

    def __repr__(self):
        return f"<ReservaEstoque(id={self.id}, pedido_id={self.pedido_id}, qtd={self.quantidade_reservada})>"
