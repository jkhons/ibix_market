# PDV Ibix - Report Definition (E-Relatórios)
# Catálogo opcional de relatórios (registry em código é primário; tabela para seeds/admin).
from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func

from ..database.base import Base


class ReportDefinition(Base):
    """Catálogo de relatórios disponíveis (opcional; registry em código é primário)."""
    __tablename__ = "report_definitions"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    report_key = Column(String(128), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    output_formats = Column(ARRAY(Text), nullable=False, default=["pdf"])
    required_module = Column(String(64), nullable=True)
    required_perm = Column(String(128), nullable=True)
    param_schema = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<ReportDefinition(report_key='{self.report_key}', name='{self.name}')>"
