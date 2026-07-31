# PDV Ibix — Campanha de marketing operacional (plataforma / Superadmin)
from sqlalchemy import CheckConstraint, Column, Date, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from ..database.base import Base


class MarketingCampanha(Base):
    """Campanha editorial operacional (ex.: lançamento 40 dias). Sem tenant_id."""

    __tablename__ = "marketing_campanhas"
    __table_args__ = (
        CheckConstraint("status IN ('ativa', 'encerrada')", name="ck_marketing_campanhas_status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    slug = Column(String(80), nullable=False, unique=True)
    titulo = Column(String(200), nullable=False)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    canais = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, server_default="ativa")
    proximo_passo = Column(Text, nullable=False)
    formato = Column(Text, nullable=True)
    tom = Column(Text, nullable=True)
    linha_gancho = Column(String(80), nullable=True)
    frase_ancora = Column(Text, nullable=True)
    linha_editorial = Column(Text, nullable=True)
    ritmo_resumo = Column(Text, nullable=True)
    politica_reuso = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
