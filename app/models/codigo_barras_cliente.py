# PDV Ibix - Códigos de barras por produto (estabelecimento)
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class CodigoBarrasCliente(BaseModel):
    """Múltiplos códigos de barras por produto_cliente. Código globalmente único."""
    __tablename__ = "codigos_barras_cliente"

    produto_cliente_id = Column(
        Integer,
        ForeignKey("produtos_cliente.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codigo_barras = Column(String(50), nullable=False)
    principal = Column(Boolean, nullable=False, default=False)

    produto_cliente = relationship("ProdutoCliente", back_populates="codigos_barras")

    __table_args__ = (UniqueConstraint("codigo_barras", name="uq_codigos_barras_cliente_codigo"),)
