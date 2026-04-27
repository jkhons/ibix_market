# PDV Ibix — Configuração global da vitrine (singleton id=1)
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from ..database.base import Base


class MarketingVitrineConfig(Base):
    """Uma única linha (id=1) com parâmetros globais da home da vitrine."""

    __tablename__ = "marketing_vitrine_config"

    id = Column(Integer, primary_key=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    mostrar_todos_produtos = Column(Boolean, nullable=False, server_default="true")
    titulo_ofertas_semana = Column(String(200), nullable=True)
    subtitulo_ofertas_semana = Column(Text(), nullable=True)
    ativo = Column(Boolean, nullable=False, server_default="true")
    mostrar_hero_carrossel = Column(Boolean, nullable=False, server_default="true")
    mostrar_secao_em_alta = Column(Boolean, nullable=False, server_default="true")
    mostrar_secao_lojas_destaque = Column(Boolean, nullable=False, server_default="true")
    # Limita quantos itens aparecem em "Ofertas da semana" (bloco oferta_semana).
    # Mantém compatibilidade com o MAPA_DE_API: até 8 por bloco.
    limite_ofertas_semana = Column(Integer, nullable=False, server_default="8")
    titulo_faixa_destaques = Column(String(200), nullable=True)
    # Faixa «Destaques»: parametrizado pelo Superadmin (PATCH /marketing-vitrine/config).
    destaque_layout = Column(String(20), nullable=False, server_default="carrossel")
    destaque_mostrar_setas = Column(Boolean, nullable=False, server_default="true")
    destaque_scroll_snap = Column(Boolean, nullable=False, server_default="true")
    # Ordem dos cards na faixa: embaralhada em cada GET vitrine-home / SSR quando true.
    destaque_embaralhar = Column(Boolean, nullable=False, server_default="false")
    titulo_em_alta = Column(String(200), nullable=True)
    subtitulo_em_alta = Column(Text(), nullable=True)
    updated_by = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
