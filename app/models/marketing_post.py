# PDV Ibix — Post operacional da campanha de marketing (plataforma / Superadmin)
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.sql import func

from ..database.base import Base


class MarketingPost(Base):
    """Post da campanha: calendário fixo + status operacional editável."""

    __tablename__ = "marketing_posts"
    __table_args__ = (
        UniqueConstraint("campanha_id", "numero", name="uq_marketing_posts_campanha_numero"),
        CheckConstraint("bloco IN ('A', 'B', 'C', 'D')", name="ck_marketing_posts_bloco"),
        CheckConstraint("tipo IN ('cheio', 'leve', 'reuso')", name="ck_marketing_posts_tipo"),
        CheckConstraint(
            "status_copy IN ('proposta', 'aprovado', 'rejeitado')",
            name="ck_marketing_posts_status_copy",
        ),
        CheckConstraint(
            "status_producao IN ('pendente', 'gravado', 'pronto')",
            name="ck_marketing_posts_status_producao",
        ),
        CheckConstraint(
            "status_publicacao IN ('pendente', 'ig', 'fb', 'ambos')",
            name="ck_marketing_posts_status_publicacao",
        ),
        Index("ix_marketing_posts_campanha_data", "campanha_id", "data_prevista"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    campanha_id = Column(
        Integer,
        ForeignKey("marketing_campanhas.id", ondelete="CASCADE"),
        nullable=False,
    )
    numero = Column(Integer, nullable=False)
    data_prevista = Column(Date, nullable=False)
    bloco = Column(String(1), nullable=False)
    tipo = Column(String(10), nullable=False)
    tema = Column(Text, nullable=False)
    angulo = Column(Text, nullable=False)
    copy_ref = Column(String(200), nullable=True)
    duracao = Column(String(120), nullable=True)
    legenda_reels = Column(Text, nullable=True)
    roteiro_notas = Column(Text, nullable=True)
    telas_necessarias = Column(Text, nullable=True)
    cortes = Column(JSON, nullable=True)
    status_copy = Column(String(20), nullable=False, server_default="proposta")
    telas_ok = Column(Boolean, nullable=False, server_default="false")
    status_producao = Column(String(20), nullable=False, server_default="pendente")
    status_publicacao = Column(String(20), nullable=False, server_default="pendente")
    publicado_em = Column(DateTime(timezone=True), nullable=True)
    chk_texto_curto = Column(Boolean, nullable=False, server_default="false")
    chk_tela_real = Column(Boolean, nullable=False, server_default="false")
    chk_mesmo_ig_fb = Column(Boolean, nullable=False, server_default="false")
    chk_frase_ancora = Column(Boolean, nullable=False, server_default="false")
    chk_entrega_regra = Column(Boolean, nullable=False, server_default="false")
    chk_stories_mesmo_dia = Column(Boolean, nullable=False, server_default="false")
    reuso_origem_numero = Column(Integer, nullable=True)
    notas = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    # Soft ref a usuarios.id (role app sem privilege REFERENCES em usuarios).
    updated_by_user_id = Column(Integer, nullable=True)
