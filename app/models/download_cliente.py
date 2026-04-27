# PDV Ibix - Modelo DownloadCliente
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.base import BaseModel


class DownloadCliente(BaseModel):
    """Modelo para tabela downloads_cliente"""
    __tablename__ = "downloads_cliente"
    
    # Colunas
    area_cliente_id = Column(Integer, ForeignKey("areas_cliente.id"), nullable=False)
    tipo_documento = Column(String(50), nullable=False)  # certificado, relatorio, comprovante
    nome_arquivo = Column(String(255), nullable=False)
    caminho_arquivo = Column(String(500), nullable=False)
    tamanho_arquivo = Column(Integer, nullable=True)  # em bytes
    formato_arquivo = Column(String(10), nullable=False)  # pdf, doc, xls
    data_download = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_download = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    status_download = Column(String(20), default="iniciado")  # iniciado, concluido, falha
    tentativas = Column(Integer, default=1)
    
    # Relacionamentos
    area_cliente = relationship("AreaCliente", back_populates="downloads_cliente")
    
    # Índices
    __table_args__ = (
        {"comment": "Tabela para registrar downloads de documentos pelos clientes"}
    ) 