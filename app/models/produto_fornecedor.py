# PDV Ibix - Vínculo produto-fornecedor (código e preço no fornecedor)
from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class ProdutoFornecedor(BaseModel):
    """Associação produto_cliente ↔ fornecedor_cliente com código e preço de compra.
    Mapa cProd fornecedor → produto_cliente_id (entrada NFe). UNIQUE(fornecedor_cliente_id, codigo_fornecedor)."""
    __tablename__ = "produtos_fornecedor"

    produto_cliente_id = Column(
        Integer,
        ForeignKey("produtos_cliente.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fornecedor_cliente_id = Column(
        Integer,
        ForeignKey("fornecedores_cliente.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codigo_fornecedor = Column(String(50), nullable=True)
    preco_compra = Column(Numeric(10, 2), nullable=True)
    # Extensão módulo entrada NFe
    xprod_amostra = Column(String(500), nullable=True, comment="Última descrição vista no XML (xProd)")
    ean_amostra = Column(String(14), nullable=True)
    ucom_amostra = Column(String(10), nullable=True)
    fator_conversao = Column(Numeric(18, 6), nullable=False, default=1, server_default="1")
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")

    produto_cliente = relationship("ProdutoCliente", back_populates="produtos_fornecedor")
    fornecedor_cliente = relationship("FornecedorCliente", back_populates="produtos_fornecedor")

    __table_args__ = (UniqueConstraint("fornecedor_cliente_id", "codigo_fornecedor", name="uq_produtos_fornecedor_fornecedor_codigo"),)
