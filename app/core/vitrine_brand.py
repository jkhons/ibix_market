# PDV Ibix — Marca visual da vitrine (logo do header, URLs absolutas para e-mail)
"""Fonte canônica multi-brand: brand.logo_url; override opcional em configuracoes (legado Ibix)."""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.billing_config import get_app_url
from app.models.configuracao import Configuracao
from app.services.brand_service import BrandContext

CHAVE_MARKETPLACE_EMAIL_LOGO_PLATAFORMA_URL = "marketplace_email_logo_plataforma_url"
# Legado — preferir brand.logo_url
VITRINE_HEADER_LOGO_PATH = "/static/img/ibix/cab.png"


def _cfg(db: Session, chave: str) -> str:
    row = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    return (row.valor or "").strip() if row else ""


def absolute_public_url(
    db: Session,
    url_or_path: Optional[str],
    *,
    public_base: Optional[str] = None,
) -> str:
    raw = (url_or_path or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        return raw
    base = (public_base or "").strip().rstrip("/")
    if not base:
        base = (get_app_url(db) or "").strip().rstrip("/")
    if not base:
        return ""
    if raw.startswith("/"):
        return f"{base}{raw}"
    return f"{base}/{raw}"


def resolve_vitrine_header_logo_url(
    db: Session,
    brand: Optional[BrandContext] = None,
) -> str:
    """URL absoluta do logo do header da vitrine, com override opcional em configuracoes."""
    logo_cfg = _cfg(db, CHAVE_MARKETPLACE_EMAIL_LOGO_PLATAFORMA_URL)
    pub_base = (brand.seo_base_url if brand else None) or None
    if logo_cfg:
        return absolute_public_url(db, logo_cfg, public_base=pub_base)
    path = (brand.logo_url if brand else None) or VITRINE_HEADER_LOGO_PATH
    return absolute_public_url(db, path, public_base=pub_base)


def build_vitrine_logo_email_html(
    db: Session,
    *,
    brand: Optional[BrandContext] = None,
    alt: Optional[str] = None,
    max_width_px: int = 280,
    link_href: Optional[str] = None,
) -> str:
    """Bloco <img> (ou link+img) para e-mails marketplace."""
    alt_text = alt or (brand.nome_curto if brand else None) or (brand.nome_exibicao if brand else None) or "Ibix"
    url = resolve_vitrine_header_logo_url(db, brand=brand)
    if not url:
        return f'<span style="font-size:26px;font-weight:700;color:#2F3A44;letter-spacing:0.02em;">{alt_text}</span>'
    esc = alt_text.replace('"', "&quot;")
    mw = int(max_width_px)
    img = (
        f'<img src="{url}" alt="{esc}" width="{mw}" '
        f'style="display:block;margin:0 auto;max-width:{mw}px;width:100%;height:auto;border:0;outline:none;text-decoration:none;">'
    )
    if link_href:
        return (
            f'<a href="{link_href}" target="_blank" rel="noopener noreferrer" '
            f'style="text-decoration:none;display:inline-block;">{img}</a>'
        )
    return img


__all__ = [
    "VITRINE_HEADER_LOGO_PATH",
    "CHAVE_MARKETPLACE_EMAIL_LOGO_PLATAFORMA_URL",
    "absolute_public_url",
    "resolve_vitrine_header_logo_url",
    "build_vitrine_logo_email_html",
]
