# PDV Ibix - Modelo AlertaEmail
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database.base import BaseModel

if TYPE_CHECKING:
    pass

class AlertaEmail(BaseModel):
    """Modelo para tabela alertas_email"""
    __tablename__ = "alertas_email"
    
    # Colunas
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    tipo_alerta = Column(String(50), nullable=False)  # vencimento, renovacao, manutencao
    email_destino = Column(String(100), nullable=False)
    assunto = Column(String(200), nullable=False)
    mensagem = Column(Text, nullable=False)
    agendado_para = Column(DateTime(timezone=True), nullable=False)
    enviado = Column(Boolean, default=False)
    data_envio = Column(DateTime(timezone=True), nullable=True)
    tentativas = Column(Integer, default=0)
    status = Column(String(20), default="pendente")  # pendente, enviado, falha, cancelado
    
    # Relacionamentos
    cliente = relationship("Cliente", back_populates="alertas_email")
    alertas_enviados = relationship("AlertaEnviado", back_populates="alerta_email", cascade="all, delete-orphan")
    
    # Índices
    __table_args__ = (
        {"comment": "Tabela para agendar e controlar envio de alertas por email"}
    ) 