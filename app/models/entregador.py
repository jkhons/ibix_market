# PDV Ibix - Entregador (logística local)
# Entregador é ator separado: NULL tenant_id = plataforma; preenchido = privado/vinculado ao tenant.
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass


class Entregador(BaseModel):
    """Cadastro do entregador (entrega na cidade). Não é Usuario/tenant."""
    __tablename__ = "entregadores"

    nome = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, unique=True, index=True)
    senha_hash = Column(String(255), nullable=False)
    telefone = Column(String(30), nullable=True)
    cpf = Column(String(20), nullable=True)
    tipo_veiculo = Column(String(20), nullable=True)  # moto, carro, utilitario
    ativo = Column(Boolean, nullable=False, server_default="true")
    status = Column(String(30), nullable=False, server_default="ativo", index=True)  # ativo, bloqueado, pendente
    tenant_id = Column(Integer, nullable=True, index=True)  # NULL = plataforma; preenchido = vinculado ao tenant
    cidade = Column(String(100), nullable=True, index=True)

    entregas = relationship("EntregaMarketplace", back_populates="entregador", foreign_keys="EntregaMarketplace.entregador_id")
    veiculos = relationship("EntregadorVeiculo", back_populates="entregador", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Entregador(id={self.id}, email='{self.email}', tipo_veiculo='{self.tipo_veiculo}')>"
