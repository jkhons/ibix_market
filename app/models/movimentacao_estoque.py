# PDV Ibix - Movimentações de estoque por produto (estabelecimento)
from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class MovimentacaoEstoque(BaseModel):
    """Registro de entrada/saída/ajuste/transferência por produto_cliente.
    Vínculo fiscal: nfe_documento_id/nfe_item_id para rastreabilidade (entrada NFe).
    Constraint única em nfe_item_id evita movimentos duplicados por item de NF-e."""
    __tablename__ = "movimentacoes_estoque"
    __table_args__ = (UniqueConstraint("nfe_item_id", name="uq_movimentacoes_estoque_nfe_item_id"),)

    produto_cliente_id = Column(
        Integer,
        ForeignKey("produtos_cliente.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo = Column(String(20), nullable=False, comment="entrada, saida, ajuste, transferencia")
    quantidade = Column(Numeric(10, 2), nullable=False)
    valor_unitario = Column(Numeric(10, 2), nullable=True)
    documento_ref = Column(String(100), nullable=True)
    observacao = Column(Text(), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    # Extensão módulo entrada NFe
    nfe_documento_id = Column(
        Integer,
        ForeignKey("nfe_documentos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nfe_item_id = Column(
        Integer,
        ForeignKey("nfe_itens.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    custo_total = Column(Numeric(18, 2), nullable=True)

    produto_cliente = relationship("ProdutoCliente", back_populates="movimentacoes")
    usuario = relationship("Usuario", foreign_keys=[usuario_id])
    nfe_documento = relationship("NfeDocumento", foreign_keys=[nfe_documento_id])
    nfe_item = relationship("NfeItem", foreign_keys=[nfe_item_id])
