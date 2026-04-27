# PDV Ibix - Log de uso Google Custom Search (busca imagem)
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class GoogleCseUsoLog(BaseModel):
    __tablename__ = "google_cse_uso_log"

    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(32), nullable=False, default="search")

    tenant = relationship("Tenant", backref="google_cse_uso_logs")
    usuario = relationship("Usuario", foreign_keys=[usuario_id])

    __table_args__ = ({"comment": "Uma linha por busca Google CSE (imagem) bem-sucedida"},)
