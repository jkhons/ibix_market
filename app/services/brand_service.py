# PDV Ibix — Resolução de marca por Host (multi-brand Fase 1)
"""Ibix = marca origem (is_origem). Campos visuais nulos na marca derivada herdam da origem (default de marca, não fallback de negócio)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.brand import Brand, BrandDomain


@dataclass(frozen=True)
class BrandContext:
    """Contexto imutável de marca para request.state e templates Jinja."""

    id: int
    slug: str
    nome_exibicao: str
    nome_curto: str
    logo_url: str
    logo_footer_url: str
    favicon_url: str
    telefone: str
    whatsapp: str
    email_remetente: str
    cor_primaria: str
    cor_secundaria: str
    seo_base_url: str
    is_origem: bool

    def to_template_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "slug": self.slug,
            "nome_exibicao": self.nome_exibicao,
            "nome_curto": self.nome_curto,
            "nome": self.nome_curto or self.nome_exibicao,
            "logo_url": self.logo_url,
            "logo_footer_url": self.logo_footer_url,
            "logo_display_url": brand_logo_display_url(self),
            "logo_footer_display_url": brand_logo_footer_display_url(self),
            "logo_mark_url": brand_logo_mark_url(self),
            "logo_wordmark_url": brand_logo_wordmark_url(self),
            "favicon_url": self.favicon_url,
            "telefone": self.telefone,
            "whatsapp": self.whatsapp,
            "email_remetente": self.email_remetente,
            "cor_primaria": self.cor_primaria,
            "cor_secundaria": self.cor_secundaria,
            "seo_base_url": self.seo_base_url,
            "is_origem": self.is_origem,
        }


def normalize_host(raw_host: Optional[str]) -> str:
    return (raw_host or "").split(":")[0].strip().lower()


_IBIX_LOGO_PATH_MARKERS = ("/ibix/", "/landing/logosfundo", "logosfundo.png")
# Lockup da origem: mascote + wordmark (assets documentados; cab.png = composição única p/ OG/e-mail)
_IBIX_LOGO_MARK_URL = "/static/img/ibix/mascote.png"
_IBIX_LOGO_WORDMARK_URL = "/static/img/ibix/escrita.png"
_IBIX_LOGO_CAB_URL = "/static/img/ibix/cab.png"


def _is_ibix_shared_logo_asset(logo: str, slug: str) -> bool:
    """True se o path aponta para asset Ibix ou placeholder copiado (ex.: solumatica/cab.png)."""
    low = (logo or "").lower()
    if any(m in low for m in _IBIX_LOGO_PATH_MARKERS):
        return True
    if slug == "solumatica" and ("/solumatica/cab.png" in low or "/solumatica/rodape.png" in low):
        return True
    return False


def brand_logo_display_url(ctx: BrandContext) -> str:
    """URL para <img> na UI ou vazio (somente texto da marca). Marca derivada sem logo próprio → ''."""
    logo = (ctx.logo_url or "").strip()
    if ctx.is_origem:
        return logo or _IBIX_LOGO_CAB_URL
    if not logo or _is_ibix_shared_logo_asset(logo, ctx.slug):
        return ""
    return logo


def brand_logo_footer_display_url(ctx: BrandContext) -> str:
    footer = (ctx.logo_footer_url or ctx.logo_url or "").strip()
    if ctx.is_origem:
        return footer or "/static/img/ibix/rodape.png"
    if not footer or _is_ibix_shared_logo_asset(footer, ctx.slug):
        return ""
    return footer


def brand_logo_mark_url(ctx: BrandContext) -> str:
    """Mascote do lockup (só origem / assets Ibix). Vazio → UI usa logo_display único."""
    if not ctx.is_origem:
        return ""
    logo = (ctx.logo_url or "").strip()
    if logo and not _is_ibix_shared_logo_asset(logo, ctx.slug):
        return ""
    return _IBIX_LOGO_MARK_URL


def brand_logo_wordmark_url(ctx: BrandContext) -> str:
    """Wordmark do lockup (só origem / assets Ibix)."""
    if not ctx.is_origem:
        return ""
    logo = (ctx.logo_url or "").strip()
    if logo and not _is_ibix_shared_logo_asset(logo, ctx.slug):
        return ""
    return _IBIX_LOGO_WORDMARK_URL


def _pick_visual(origin_val: Optional[str], brand_val: Optional[str]) -> str:
    """Herança visual: valor da marca derivada ou, se vazio, da origem."""
    b = (brand_val or "").strip()
    if b:
        return b
    return (origin_val or "").strip()


def _brand_row_to_context(brand: Brand, origin: Optional[Brand]) -> BrandContext:
    orig = origin if origin and origin.id != brand.id else None
    o_logo = (orig.logo_url if orig else brand.logo_url) or _IBIX_LOGO_CAB_URL
    o_footer = (orig.logo_footer_url if orig else brand.logo_footer_url) or o_logo
    o_favicon = (orig.favicon_url if orig else brand.favicon_url) or "/static/img/arte-pdv.png"
    o_nome = (orig.nome_exibicao if orig else brand.nome_exibicao) or "Ibix"
    o_curto = (orig.nome_curto if orig else brand.nome_curto) or o_nome
    o_seo = (orig.seo_base_url if orig else brand.seo_base_url) or ""

    return BrandContext(
        id=brand.id,
        slug=brand.slug,
        nome_exibicao=_pick_visual(o_nome, brand.nome_exibicao) or o_nome,
        nome_curto=_pick_visual(o_curto, brand.nome_curto) or _pick_visual(o_nome, brand.nome_exibicao) or o_nome,
        logo_url=_pick_visual(o_logo, brand.logo_url) or o_logo,
        logo_footer_url=_pick_visual(o_footer, brand.logo_footer_url) or _pick_visual(o_logo, brand.logo_url) or o_logo,
        favicon_url=_pick_visual(o_favicon, brand.favicon_url) or o_favicon,
        telefone=_pick_visual(orig.telefone if orig else "", brand.telefone),
        whatsapp=_pick_visual(orig.whatsapp if orig else "", brand.whatsapp),
        email_remetente=_pick_visual(orig.email_remetente if orig else "", brand.email_remetente),
        cor_primaria=_pick_visual(orig.cor_primaria if orig else "", brand.cor_primaria),
        cor_secundaria=_pick_visual(orig.cor_secundaria if orig else "", brand.cor_secundaria),
        seo_base_url=_pick_visual(o_seo, brand.seo_base_url) or o_seo,
        is_origem=bool(brand.is_origem),
    )


def get_origin_brand(db: Session) -> Brand:
    row = (
        db.query(Brand)
        .filter(Brand.is_origem.is_(True), Brand.ativo.is_(True))
        .order_by(Brand.id.asc())
        .first()
    )
    if not row:
        raise RuntimeError(
            "Marca origem (is_origem=true) não configurada. Execute a migração br01_multibrand_brands_domains."
        )
    return row


def resolve_brand_by_host(db: Session, host: str) -> BrandContext:
    """Resolve marca pelo Host. Host desconhecido → marca origem (Ibix)."""
    from app.core.redis_cache import get_brand_by_host_cached

    norm = normalize_host(host)

    def _fetch() -> BrandContext:
        origin = get_origin_brand(db)
        if not norm:
            return _brand_row_to_context(origin, None)

        domain_row = (
            db.query(BrandDomain)
            .join(Brand, Brand.id == BrandDomain.brand_id)
            .filter(
                BrandDomain.dominio == norm,
                BrandDomain.ativo.is_(True),
                Brand.ativo.is_(True),
            )
            .first()
        )
        if domain_row:
            brand = db.query(Brand).filter(Brand.id == domain_row.brand_id).first()
            if brand:
                return _brand_row_to_context(brand, origin if not brand.is_origem else None)

        return _brand_row_to_context(origin, None)

    return get_brand_by_host_cached(norm or "__empty__", lambda: _fetch())


def brand_context_from_request(request) -> Optional[BrandContext]:
    return getattr(request.state, "brand", None)


__all__ = [
    "BrandContext",
    "normalize_host",
    "brand_logo_display_url",
    "brand_logo_footer_display_url",
    "brand_logo_mark_url",
    "brand_logo_wordmark_url",
    "get_origin_brand",
    "resolve_brand_by_host",
    "brand_context_from_request",
]
