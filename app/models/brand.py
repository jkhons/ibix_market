# PDV Ibix - Marca (multi-brand: Ibix origem, Solumática, futuro Certipeso)
from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database.base import BaseModel


class Brand(BaseModel):
    """Marca/produto white-label (visual, domínios, SEO). Ibix: is_origem=True."""

    __tablename__ = "brands"

    slug = Column(String(50), nullable=False, unique=True, index=True)
    nome_exibicao = Column(String(255), nullable=False)
    nome_curto = Column(String(80), nullable=True, comment="Nome curto (alt, tagline)")
    logo_url = Column(String(500), nullable=False)
    logo_footer_url = Column(String(500), nullable=True)
    favicon_url = Column(String(500), nullable=True)
    telefone = Column(String(30), nullable=True)
    whatsapp = Column(String(30), nullable=True)
    email_remetente = Column(String(255), nullable=True)
    cor_primaria = Column(String(20), nullable=True)
    cor_secundaria = Column(String(20), nullable=True)
    seo_base_url = Column(String(500), nullable=True)
    is_origem = Column(Boolean, nullable=False, default=False, server_default="false")
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")

    domains = relationship("BrandDomain", back_populates="brand", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_brands_ativo", "ativo"),
        Index("ix_brands_is_origem", "is_origem"),
        {"comment": "Marcas white-label (Ibix origem, Solumática, etc.)"},
    )

    def __repr__(self):
        return f"<Brand(id={self.id}, slug='{self.slug}', is_origem={self.is_origem})>"


class BrandDomain(BaseModel):
    """Domínio HTTP(S) autorizado → marca (allowlist anti Host header injection)."""

    __tablename__ = "brand_domains"

    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    dominio = Column(String(255), nullable=False, comment="Host sem porta, lowercase")
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")

    brand = relationship("Brand", back_populates="domains")

    __table_args__ = (
        UniqueConstraint("dominio", name="uq_brand_domains_dominio"),
        Index("ix_brand_domains_brand_ativo", "brand_id", "ativo"),
        {"comment": "Mapeamento domínio → marca"},
    )

    def __repr__(self):
        return f"<BrandDomain(brand_id={self.brand_id}, dominio='{self.dominio}')>"
