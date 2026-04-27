# PDV Ibix - Notificação Lida Model
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class NotificacaoLida(BaseModel):
    """Modelo para notificações lidas por usuário"""
    __tablename__ = "notificacoes_lidas_usuario"
    
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    notificacao_id = Column(String(255), nullable=False)
    tipo_notificacao = Column(
        Enum('agendamento_hoje', 'novo_agendamento', 'certificado_vencendo', 'contrato_vencendo', name='tipo_notificacao_enum'),
        nullable=False
    )
    data_leitura = Column(DateTime, nullable=False, default=datetime.now)
    
    # Relacionamento
    usuario = relationship("Usuario", foreign_keys=[usuario_id])
    
    def __repr__(self):
        return f"<NotificacaoLida(usuario_id={self.usuario_id}, notificacao_id='{self.notificacao_id}')>"

