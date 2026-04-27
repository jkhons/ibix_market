# PDV Ibix - Status de pedido marketplace (configurável pelo Super Admin)
"""Lista global de status para pedidos da loja (marketplace). Sem tenant_id."""
from sqlalchemy import Boolean, Column, Integer, String

from ..database.base import BaseModel


class StatusPedidoMarketplace(BaseModel):
    """Status configurável para pedidos da loja. Super Admin gerencia; CA usa na listagem e alteração."""
    __tablename__ = "status_pedido_marketplace"

    codigo = Column(String(30), nullable=False, unique=True, index=True)
    label = Column(String(100), nullable=False)
    ordem = Column(Integer, nullable=False, server_default="0")
    ativo = Column(Boolean, nullable=False, server_default="true")

    def __repr__(self):
        return f"<StatusPedidoMarketplace(id={self.id}, codigo='{self.codigo}', label='{self.label}')>"
