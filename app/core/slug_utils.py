import re
import unicodedata
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED_ROOT_SLUGS = {
    "api",
    "admin",
    "login",
    "logout",
    "register",
    "cadastro",
    "cadastro-representante",
    "cadastro-influencer",
    "change-password",
    "dashboard",
    "clientes",
    "planos",
    "portal",
    "roles",
    "relatorios",
    "configuracoes",
    "usuarios",
    "minha-equipe",
    "email-cliente",
    "blank",
    "help-center",
    "manual",
    "changelog",
    "representantes",
    "influencers-loja",
    "entregas",
    "entregador",
    "billing",
    "auth",
    "negocio",
    "fiscal",
    "financeiro",
    "influencer",
    "ui",
    "categoria",
    "produto",
    "static",
    "assets",
    "favicon-ico",
    "robots-txt",
    "sitemap-xml",
    "loja",
    "lojas-parceiras",
    "como-funciona-vitrine",
    "politica-privacidade",
    "politica-privacidade-marketplace",
    "termos-de-uso",
    "merchant-feed",
    "i",
}


def slugify(value: str) -> str:
    text = (value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def normalize_slug_or_400(raw_value: str, *, field_name: str = "Slug", max_len: int = 100) -> str:
    slug = slugify(raw_value)
    if not slug or not SLUG_REGEX.match(slug):
        raise HTTPException(status_code=400, detail=f"{field_name} inválido. Use letras, números e hífen.")
    if len(slug) > max_len:
        raise HTTPException(status_code=400, detail=f"{field_name} inválido. Máximo de {max_len} caracteres.")
    return slug


def normalize_slug_or_404(raw_value: str) -> str:
    slug = slugify(raw_value)
    if not slug or not SLUG_REGEX.match(slug):
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return slug


def ensure_slug_not_reserved(slug: str) -> None:
    normalized = slugify(slug)
    if normalized in RESERVED_ROOT_SLUGS:
        raise HTTPException(status_code=400, detail="Slug reservado. Escolha outro slug para a loja.")


def normalize_city_slug(raw_city: str) -> str:
    return normalize_slug_or_400(raw_city, field_name="Cidade", max_len=120)


def normalize_category_slug(raw_category: str) -> str:
    return normalize_slug_or_400(raw_category, field_name="Categoria", max_len=120)


def generate_unique_slug(
    db: Session,
    model,
    base_slug: str,
    *,
    field_name: str = "slug",
    exclude_id: int | None = None,
) -> str:
    slug = base_slug
    counter = 2
    while True:
        query = db.query(model).filter(func.lower(getattr(model, field_name)) == slug)
        if exclude_id is not None:
            query = query.filter(model.id != exclude_id)
        if not query.first():
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def produto_slug_url(titulo: str, anuncio_id: int) -> str:
    """SEO-friendly product URL: /loja/produto/{slug}-{id}"""
    slug = slugify(titulo or "produto")
    if not slug:
        slug = "produto"
    return f"/loja/produto/{slug}-{anuncio_id}"


def parse_produto_slug_id(slug_id: str) -> int | None:
    """Extract anuncio_id from '{slug}-{id}' pattern. Returns None if invalid."""
    parts = slug_id.rsplit("-", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return int(parts[1])
    if slug_id.isdigit():
        return int(slug_id)
    return None


def first_non_empty(values: Iterable[str | None]) -> str | None:
    for value in values:
        if value is None:
            continue
        clean = str(value).strip()
        if clean:
            return clean
    return None
