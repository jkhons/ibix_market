# PDV Ibix - Eventos para integração CRM (pull pelo servidor externo)
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from ..database.base import BaseModel


class IntegrationEvent(BaseModel):
    """Evento de negócio para consumo pela API de integração (CRM externo)."""
    __tablename__ = "integration_events"

    tenant_id = Column(Integer, nullable=False, index=True)  # clientes.id (estabelecimento)
    event_name = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    payload_json = Column(JSONB(), nullable=False)
    status = Column(String(20), nullable=False, server_default="pending", index=True)
    retry_count = Column(Integer, nullable=False, server_default="0")
    last_error = Column(Text(), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<IntegrationEvent(id={self.id}, event_name='{self.event_name}', entity_type='{self.entity_type}', entity_id={self.entity_id})>"
