# PDV Ibix - Modelo AlertaEnviado
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import BaseModel


class AlertaEnviado(BaseModel):
    """Modelo para tabela alertas_enviados"""
    __tablename__ = "alertas_enviados"
    
    # Colunas
    alerta_email_id = Column(Integer, ForeignKey("alertas_email.id"), nullable=False)
    tipo_alerta = Column(String(50), nullable=False)  # vencimento, renovacao, manutencao
    destinatario = Column(String(100), nullable=False)
    assunto = Column(String(200), nullable=False)
    conteudo = Column(Text, nullable=False)
    data_envio = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status_envio = Column(String(20), nullable=False)  # sucesso, falha, pendente
    erro_mensagem = Column(Text, nullable=True)
    tentativas = Column(Integer, default=1)
    servidor_smtp = Column(String(100), nullable=True)
    ip_origem = Column(String(45), nullable=True)
    
    # Relacionamentos
    alerta_email = relationship("AlertaEmail", back_populates="alertas_enviados")
    
    # Índices
    __table_args__ = (
        {"comment": "Tabela para registrar histórico de alertas enviados"}
    ) 