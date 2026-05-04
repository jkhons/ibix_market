# PDV Ibix - Veículos do Entregador (N veículos por entregador)
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class EntregadorVeiculo(BaseModel):
    """Veículo vinculado a um entregador. Cada entregador pode ter N veículos."""
    __tablename__ = "entregador_veiculos"

    entregador_id = Column(
        Integer,
        ForeignKey("entregadores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_veiculo = Column(String(20), nullable=True)
    capacidade_kg = Column(Numeric(10, 2), nullable=True)
    descricao = Column(String(100), nullable=True)
    placa = Column(String(10), nullable=True)
    ativo = Column(Boolean, nullable=False, server_default="true")
    documento_veiculo_path = Column(String(500), nullable=True)
    documento_aprovado = Column(Boolean, nullable=False, server_default="false")
    documento_aprovado_em = Column(DateTime(timezone=True), nullable=True)
    documento_aprovado_por_usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)

    entregador = relationship("Entregador", back_populates="veiculos")

    __table_args__ = (
        UniqueConstraint("entregador_id", "placa", name="uq_entregador_placa"),
    )

    def __repr__(self):
        return f"<EntregadorVeiculo(id={self.id}, entregador_id={self.entregador_id}, tipo='{self.tipo_veiculo}')>"
