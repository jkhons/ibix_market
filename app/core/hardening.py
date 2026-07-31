# PDV Ibix — Hardening multi-brand (Fase 5: CORS, CSP, métricas)
"""Allowlist CORS a partir de brand_domains + env; CSP por marca; escopo de rate limit."""
from __future__ import annotations

import os
from typing import Iterable, Optional, Sequence
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.brand import Brand, BrandDomain
from app.services.brand_service import BrandContext

_DEFAULT_IBIX_ORIGINS = (
    "https://www.ibix.com.br",
    "https://ibix.com.br",
)


def _origin_from_host(host: str, *, https: bool = True) -> str:
    host = host.strip().lower()
    if not host:
        return ""
    scheme = "https" if https else "http"
    return f"{scheme}://{host}"


def _origin_from_url(url: str) -> Optional[str]:
    raw = (url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    if not parsed.netloc:
        return None
    scheme = parsed.scheme or "https"
    return f"{scheme}://{parsed.netloc.lower()}"


def _related_origins_from_host(host: str) -> set[str]:
    """Gera origens HTTPS para host e variantes www/apex."""
    host = host.strip().lower()
    if not host:
        return set()
    out = {_origin_from_host(host)}
    if host.startswith("www."):
        out.add(_origin_from_host(host[4:]))
    elif "." in host:
        out.add(_origin_from_host(f"www.{host}"))
    return out


def origins_from_brand_rows(
    brands: Iterable[Brand],
    domains: Iterable[BrandDomain],
) -> set[str]:
    """Origens HTTPS derivadas de seo_base_url e brand_domains ativos."""
    out: set[str] = set()
    for brand in brands:
        if not getattr(brand, "ativo", True):
            continue
        origin = _origin_from_url(getattr(brand, "seo_base_url", None) or "")
        if origin:
            out.add(origin)
            host = urlparse(origin).netloc.lower()
            out.update(_related_origins_from_host(host))
    for domain in domains:
        if not getattr(domain, "ativo", True):
            continue
        host = (getattr(domain, "dominio", None) or "").strip().lower()
        if host:
            out.update(_related_origins_from_host(host))
    return out


def parse_cors_origins_env(raw: str) -> list[str]:
    return [o.strip() for o in (raw or "").split(",") if o.strip()]


def merge_cors_allowlist(*origin_groups: Sequence[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in origin_groups:
        for origin in group:
            origin = origin.strip()
            if origin and origin not in seen:
                seen.add(origin)
                merged.append(origin)
    return merged


def load_cors_origins_from_db(db: Session) -> list[str]:
    brands = db.query(Brand).filter(Brand.ativo.is_(True)).all()
    domains = db.query(BrandDomain).filter(BrandDomain.ativo.is_(True)).all()
    return sorted(origins_from_brand_rows(brands, domains))


def resolve_cors_allowlist(*, db: Optional[Session] = None, is_production: bool) -> list[str]:
    """Produção: env + brand_domains; nunca wildcard."""
    env_origins = parse_cors_origins_env(os.getenv("CORS_ORIGINS", ""))
    db_origins: list[str] = []
    if db is not None:
        db_origins = load_cors_origins_from_db(db)

    if is_production:
        base = env_origins if env_origins else list(_DEFAULT_IBIX_ORIGINS)
        result = merge_cors_allowlist(base, db_origins)
        if "*" in result:
            raise RuntimeError("CORS wildcard não permitido em produção")
        if not result:
            raise RuntimeError("CORS allowlist vazia em produção")
        return result

    if env_origins:
        return env_origins
    return ["*"]


def _brand_connect_src_hosts(brand: Optional[BrandContext]) -> list[str]:
    hosts: set[str] = {"*.ibix.com.br", "*.solumatica.com.br"}
    if brand:
        seo_origin = _origin_from_url(brand.seo_base_url)
        if seo_origin:
            host = urlparse(seo_origin).netloc.lower()
            if host:
                hosts.add(host)
                parts = host.split(".")
                if len(parts) >= 2:
                    hosts.add(f"*.{'.'.join(parts[-2:])}")
    extra = os.getenv("CSP_CONNECT_SRC_HOSTS", "").strip()
    if extra:
        for item in extra.split(","):
            item = item.strip()
            if item:
                hosts.add(item)
    return sorted(hosts)


def build_csp_header(
    brand: Optional[BrandContext] = None,
    *,
    extra_sources: str = "",
) -> str:
    """CSP OWASP com connect-src incluindo domínios da marca corrente."""
    connect_hosts = _brand_connect_src_hosts(brand)
    connect_src = "'self' " + " ".join(f"https://{h}" for h in connect_hosts)
    connect_src += (
        " https://cdn.jsdelivr.net https://api.mercadopago.com https://viacep.com.br"
        " https://www.google-analytics.com https://accounts.google.com"
        " https://oauth2.googleapis.com https://www.googleapis.com wss:"
    )
    policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com "
        "https://sdk.mercadopago.com https://www.googletagmanager.com https://www.google-analytics.com "
        "https://code.jquery.com https://maps.googleapis.com https://accounts.google.com https://www.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com "
        "https://fonts.googleapis.com; "
        "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob: https:; "
        f"connect-src {connect_src}; "
        "frame-src 'self' https://sdk.mercadopago.com https://accounts.google.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    if extra_sources:
        policy += "; " + extra_sources.strip()
    return policy


def is_metrics_client_allowed(client_ip: str) -> bool:
    """Prometheus /metrics só localhost, salvo METRICS_ALLOW_REMOTE=true (dev)."""
    if os.getenv("METRICS_ALLOW_REMOTE", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    normalized = (client_ip or "").strip()
    if normalized in ("127.0.0.1", "::1", "localhost"):
        return True
    if normalized.startswith("::ffff:"):
        return normalized.split("::ffff:", 1)[-1] == "127.0.0.1"
    return False


def rate_limit_brand_slug(request) -> str:
    brand = getattr(getattr(request, "state", None), "brand", None)
    slug = getattr(brand, "slug", None)
    return slug if slug else "unknown"


def public_origin_from_request(request) -> str:
    """Origem pública (scheme + host) para OAuth/redirect por marca."""
    from app.core.brand_cookie import request_is_https

    brand = getattr(getattr(request, "state", None), "brand", None)
    if brand and brand.seo_base_url:
        base = brand.seo_base_url.strip().rstrip("/")
        if base:
            return base
    scheme = "https" if request_is_https(request) else request.url.scheme
    host = (request.headers.get("host") or "").split(":")[0].strip()
    if not host:
        return ""
    return f"{scheme}://{host}"


__all__ = [
    "build_csp_header",
    "is_metrics_client_allowed",
    "load_cors_origins_from_db",
    "merge_cors_allowlist",
    "origins_from_brand_rows",
    "parse_cors_origins_env",
    "public_origin_from_request",
    "rate_limit_brand_slug",
    "resolve_cors_allowlist",
]
