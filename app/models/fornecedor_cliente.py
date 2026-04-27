# PDV Ibix - Fornecedores por estabelecimento (Fase 2)
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class FornecedorCliente(BaseModel):
    """Fornecedor vinculado a um estabelecimento (cliente_id)."""
    __tablename__ = "fornecedores_cliente"

    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome = Column(String(255), nullable=False)
    cnpj = Column(String(18), nullable=True)
    contato = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    telefone = Column(String(50), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)

    cliente = relationship("Cliente", backref="fornecedores_cliente")
    produtos_fornecedor = relationship("ProdutoFornecedor", back_populates="fornecedor_cliente", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "uq_fornecedores_cliente_cnpj_por_estabelecimento",
            "cliente_id", "cnpj",
            unique=True,
            postgresql_where=text("cnpj IS NOT NULL AND cnpj != ''"),
        ),
    )
