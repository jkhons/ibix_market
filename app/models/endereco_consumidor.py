# PDV Ibix - Endereços do consumidor (marketplace)
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class EnderecoConsumidor(BaseModel):
    """Endereços de entrega do consumidor final."""
    __tablename__ = "enderecos_consumidor"

    tenant_id = Column(Integer, nullable=True, index=True)  # clientes.id; NULL se consumidor órfão
    consumidor_id = Column(
        Integer,
        ForeignKey("consumidores_marketplace.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    apelido = Column(String(50), nullable=True)
    cep = Column(String(20), nullable=True)
    logradouro = Column(String(255), nullable=True)
    numero = Column(String(20), nullable=True)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=True)
    cidade = Column(String(100), nullable=True)
    uf = Column(String(2), nullable=True)
    tipo_endereco = Column(String(20), nullable=False, server_default="principal")
    referencia = Column(String(200), nullable=True)
    principal = Column(Boolean, nullable=False, server_default="false")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    consumidor = relationship("ConsumidorMarketplace", back_populates="enderecos")

    def __repr__(self):
        return f"<EnderecoConsumidor(id={self.id}, consumidor_id={self.consumidor_id})>"
