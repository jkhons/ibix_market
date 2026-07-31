# PDV Ibix — Agregações access_log para analytics da vitrine pública (Super Admin)
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, func, not_, or_
from sqlalchemy.orm import Session

from app.core.slug_utils import RESERVED_ROOT_SLUGS, parse_produto_slug_id
from app.models.access_log import AccessLog
from app.models.anuncio_plataforma import AnuncioPlataforma
from app.models.loja_marketplace import LojaMarketplace

logger = logging.getLogger(__name__)

TZ_BR = ZoneInfo("America/Sao_Paulo")

PERIODOS_VALIDOS = frozenset({"hoje", "ultimos_7_dias", "ultimos_30_dias"})
TIPOS_VISITANTE_FILTRO = frozenset({"HUMANO", "BOT", "CLOUD", "TODOS"})

_TOP_PAGINAS_LIMIT = 20
_TOP_PRODUTOS_LIMIT = 20
_TOP_LOJAS_LIMIT = 15
_SQL_PATHS_CANDIDATOS = 400

_PATH_LOJA_SLUG_RE = re.compile(r"^/[a-z0-9]+(?:-[a-z0-9]+)*$", re.IGNORECASE)


def classificar_path_vitrine(path: str | None) -> str:
    """Classifica path HTTP da vitrine para relatórios."""
    p = (path or "").strip()
    if not p:
        return "outros"
    if p == "/loja":
        return "home_marketplace"
    if p == "/lojas-parceiras":
        return "lojas_parceiras"
    if p.startswith("/categoria/"):
        return "categoria_local"
    if p.startswith("/loja/produto/"):
        return "produto"
    if p.startswith("/loja/categoria/"):
        return "categoria_plataforma"
    if p == "/loja/busca":
        return "busca"
    if p == "/loja/carrinho":
        return "carrinho"
    if p == "/loja/checkout":
        return "checkout"
    if p in ("/loja/obrigado", "/loja/pagamento/sucesso"):
        return "obrigado"
    if p == "/loja/pagamento/cancelado":
        return "pagamento_cancelado"
    if (
        p.startswith("/loja/login")
        or p.startswith("/loja/cadastro")
        or p.startswith("/loja/esqueci-senha")
        or p.startswith("/loja/redefinir-senha")
        or p.startswith("/loja/completar-cadastro")
        or p.startswith("/loja/acompanhar-pedido")
    ):
        return "auth"
    if p.startswith("/loja/minha-conta") or p.startswith("/loja/meus-pedidos"):
        return "conta_consumidor"
    if p.startswith("/loja/pagamento/"):
        return "pagamento"
    if p.startswith("/loja/"):
        return "loja_outros"
    if _PATH_LOJA_SLUG_RE.match(p):
        segment = p[1:].lower()
        if segment not in RESERVED_ROOT_SLUGS:
            return "loja_slug"
    return "outros"


def normalizar_path_agregacao(path: str | None) -> str:
    """Agrupa URLs de produto (slug canônico e redirect numérico) no mesmo anuncio_id."""
    p = (path or "").strip()
    if p.startswith("/loja/produto/"):
        slug_part = p.replace("/loja/produto/", "", 1)
        aid = parse_produto_slug_id(slug_part)
        if aid is not None:
            return f"/loja/produto/{aid}"
    return p


def filtro_paths_vitrine_publica():
    """SQLAlchemy: paths HTML da vitrine pública registrados em access_log."""
    slug_reservados = tuple(sorted(RESERVED_ROOT_SLUGS))
    loja_slug_match = and_(
        AccessLog.path.op("~")("^/[a-z0-9]+(?:-[a-z0-9]+)*$"),
        func.lower(func.substr(AccessLog.path, 2)).notin_(slug_reservados),
    )
    return or_(
        AccessLog.path == "/loja",
        AccessLog.path.startswith("/loja/"),
        AccessLog.path == "/lojas-parceiras",
        AccessLog.path.startswith("/categoria/"),
        loja_slug_match,
    )


def periodo_to_since_utc(periodo: str, now_utc: datetime | None = None) -> datetime:
    if periodo not in PERIODOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"periodo inválido: {periodo!r}. Use: hoje, ultimos_7_dias, ultimos_30_dias.",
        )
    now = now_utc or datetime.now(timezone.utc)
    if periodo == "hoje":
        today_br = now.astimezone(TZ_BR).date()
        return (
            datetime.combine(today_br, datetime.min.time())
            .replace(tzinfo=TZ_BR)
            .astimezone(timezone.utc)
        )
    if periodo == "ultimos_7_dias":
        return now - timedelta(days=7)
    return now - timedelta(days=30)


def _apply_tipo_visitante(query, tipo_visitante: str):
    if tipo_visitante == "TODOS":
        return query
    return query.filter(AccessLog.tipo_visitante == tipo_visitante)


def _base_query(db: Session, since_utc: datetime, tipo_visitante: str):
    q = db.query(AccessLog).filter(
        AccessLog.created_at >= since_utc,
        filtro_paths_vitrine_publica(),
    )
    return _apply_tipo_visitante(q, tipo_visitante)


def visitantes_vitrine_por_tipo(db: Session, since_utc: datetime) -> dict[str, int]:
    rows = (
        db.query(AccessLog.tipo_visitante, func.count(func.distinct(AccessLog.ip)))
        .filter(AccessLog.created_at >= since_utc, filtro_paths_vitrine_publica())
        .group_by(AccessLog.tipo_visitante)
        .all()
    )
    counts = {row[0]: row[1] for row in rows}
    return {
        "humanos": int(counts.get("HUMANO", 0)),
        "bots": int(counts.get("BOT", 0)),
        "cloud": int(counts.get("CLOUD", 0)),
    }


def _path_ip_rows(base, *, path_prefix: str | None = None, distinct: bool = False):
    q = base.with_entities(AccessLog.path, AccessLog.ip).filter(
        AccessLog.path.isnot(None),
    )
    if path_prefix:
        q = q.filter(AccessLog.path.startswith(path_prefix))
    if distinct:
        q = q.filter(AccessLog.ip.isnot(None)).distinct()
    return q.all()


def _distinct_path_ip(base, *, path_prefix: str | None = None) -> list[tuple[str, str | None]]:
    return _path_ip_rows(base, path_prefix=path_prefix, distinct=True)


def _mesclar_paginas_produto(path_ip_rows: list[tuple[str, str | None]]) -> list[dict[str, Any]]:
    req: dict[str, int] = defaultdict(int)
    ips: dict[str, set[str]] = defaultdict(set)
    path_exemplo: dict[str, str] = {}
    for raw_path, ip_val in path_ip_rows:
        raw = (raw_path or "").strip()
        key = normalizar_path_agregacao(raw)
        req[key] += 1
        path_exemplo.setdefault(key, raw)
        ip_s = (ip_val or "").strip()
        if ip_s:
            ips[key].add(ip_s)
    return [
        {
            "path": path_exemplo.get(k, k),
            "path_agregado": k,
            "tipo_pagina": classificar_path_vitrine(k),
            "requisicoes": req[k],
            "ips_unicos": len(ips[k]),
        }
        for k in ips
    ]


def _paginas_top(db: Session, base) -> list[dict[str, Any]]:
    """Páginas não-produto via SQL; produto via distinct path+ip mesclado por anuncio_id."""
    prod_rows = _path_ip_rows(base, path_prefix="/loja/produto/")
    prod_entries = _mesclar_paginas_produto(prod_rows)

    outros_rows = (
        base.filter(not_(AccessLog.path.startswith("/loja/produto/")))
        .with_entities(
            AccessLog.path,
            func.count(AccessLog.id).label("requisicoes"),
            func.count(func.distinct(AccessLog.ip)).label("ips_unicos"),
        )
        .group_by(AccessLog.path)
        .order_by(func.count(func.distinct(AccessLog.ip)).desc())
        .limit(_SQL_PATHS_CANDIDATOS)
        .all()
    )
    outros_entries = [
        {
            "path": row.path or "",
            "path_agregado": row.path or "",
            "tipo_pagina": classificar_path_vitrine(row.path),
            "requisicoes": int(row.requisicoes or 0),
            "ips_unicos": int(row.ips_unicos or 0),
        }
        for row in outros_rows
    ]
    merged = prod_entries + outros_entries
    merged.sort(key=lambda x: x["ips_unicos"], reverse=True)
    return merged[:_TOP_PAGINAS_LIMIT]


def _produtos_top(db: Session, base) -> list[dict[str, Any]]:
    rows = _path_ip_rows(base, path_prefix="/loja/produto/")
    req: dict[int, int] = defaultdict(int)
    ips: dict[int, set[str]] = defaultdict(set)
    for raw_path, ip_val in rows:
        slug_part = (raw_path or "").replace("/loja/produto/", "", 1)
        aid = parse_produto_slug_id(slug_part)
        if aid is None:
            continue
        req[aid] += 1
        ip_s = (ip_val or "").strip()
        if ip_s:
            ips[aid].add(ip_s)
    ranked = sorted(ips.keys(), key=lambda a: len(ips[a]), reverse=True)[:_TOP_PRODUTOS_LIMIT]
    titulos: dict[int, str] = {}
    if ranked:
        for a in db.query(AnuncioPlataforma.id, AnuncioPlataforma.titulo).filter(
            AnuncioPlataforma.id.in_(ranked)
        ):
            titulos[a.id] = (a.titulo or "").strip() or "—"
    return [
        {
            "anuncio_id": aid,
            "titulo": titulos.get(aid, "—"),
            "requisicoes": req[aid],
            "ips_unicos": len(ips[aid]),
        }
        for aid in ranked
    ]


def _lojas_top(db: Session, base) -> list[dict[str, Any]]:
    slug_reservados = tuple(sorted(RESERVED_ROOT_SLUGS))
    rows = (
        base.filter(
            AccessLog.path.op("~")("^/[a-z0-9]+(?:-[a-z0-9]+)*$"),
            func.lower(func.substr(AccessLog.path, 2)).notin_(slug_reservados),
        )
        .with_entities(
            func.lower(func.substr(AccessLog.path, 2)).label("slug"),
            func.count(AccessLog.id).label("requisicoes"),
            func.count(func.distinct(AccessLog.ip)).label("ips_unicos"),
        )
        .group_by(func.lower(func.substr(AccessLog.path, 2)))
        .order_by(func.count(func.distinct(AccessLog.ip)).desc())
        .limit(_TOP_LOJAS_LIMIT)
        .all()
    )
    slugs = [r.slug for r in rows if r.slug]
    nomes: dict[str, str] = {}
    if slugs:
        for loja in db.query(LojaMarketplace.slug, LojaMarketplace.nome_loja).filter(
            func.lower(LojaMarketplace.slug).in_(slugs)
        ):
            s = (loja.slug or "").strip().lower()
            if s:
                nomes[s] = (loja.nome_loja or "").strip() or s
    return [
        {
            "slug": row.slug,
            "path": f"/{row.slug}",
            "nome_loja": nomes.get(row.slug, row.slug),
            "requisicoes": int(row.requisicoes or 0),
            "ips_unicos": int(row.ips_unicos or 0),
        }
        for row in rows
        if row.slug
    ]


def _funil(base) -> list[dict[str, Any]]:
    pairs = _distinct_path_ip(base)
    funil_ips: dict[str, set[str]] = defaultdict(set)
    for path_val, ip_val in pairs:
        ip_s = (ip_val or "").strip()
        if not ip_s:
            continue
        tipo = classificar_path_vitrine(normalizar_path_agregacao(path_val))
        funil_ips[tipo].add(ip_s)
    return [
        {"tipo_pagina": tipo, "ips_unicos": len(ips_set)}
        for tipo, ips_set in sorted(funil_ips.items(), key=lambda x: -len(x[1]))
    ]


def build_visitantes_vitrine_analytics(
    db: Session,
    *,
    periodo: str,
    tipo_visitante: str = "HUMANO",
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    if tipo_visitante not in TIPOS_VISITANTE_FILTRO:
        raise HTTPException(
            status_code=400,
            detail=f"tipo_visitante inválido: {tipo_visitante!r}. Use: HUMANO, BOT, CLOUD, TODOS.",
        )
    since = periodo_to_since_utc(periodo, now_utc)
    now = now_utc or datetime.now(timezone.utc)
    base = _base_query(db, since, tipo_visitante)

    return {
        "periodo": periodo,
        "tipo_visitante_filtro": tipo_visitante,
        "gerado_em": now.isoformat(),
        "nota_metrica": (
            "ips_unicos = endereços IP distintos no período. "
            "Produtos: somente páginas /loja/produto/… (visualização na vitrine da loja /{slug} não entra aqui)."
        ),
        "paginas_top": _paginas_top(db, base),
        "produtos_top": _produtos_top(db, base),
        "lojas_top": _lojas_top(db, base),
        "funil": _funil(base),
    }
