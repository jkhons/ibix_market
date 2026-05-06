# PDV Ibix - Service para busca (autocomplete + populares)
import logging
from typing import List

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.models.anuncio_plataforma import AnuncioPlataforma
from app.models.categoria_plataforma import CategoriaPlataforma
from app.models.loja_marketplace import LojaMarketplace
from app.models.termo_buscado import TermoBuscado

logger = logging.getLogger(__name__)


def _escape_like(value: str) -> str:
    """Escapa caracteres especiais de LIKE/ILIKE (%_\\)."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def autocomplete(db: Session, termo: str, limit: int = 8) -> List[str]:
    """Sugestões de busca: combina nomes de lojas (Tenant CA), categorias e títulos
    de anúncios. Lojas ganham prioridade no topo (são entidades de alto sinal para
    o usuário que digita um nome conhecido)."""
    if not termo or len(termo) < 2:
        return []

    escaped = _escape_like(termo.lower())
    pattern = f"%{escaped}%"

    lojas = (
        db.query(
            func.coalesce(LojaMarketplace.nome_fantasia, LojaMarketplace.nome_loja).label("nome")
        )
        .filter(
            LojaMarketplace.status == "ativo",
            LojaMarketplace.slug.isnot(None),
            or_(
                LojaMarketplace.nome_loja.ilike(pattern),
                LojaMarketplace.nome_fantasia.ilike(pattern),
                LojaMarketplace.slug.ilike(pattern),
            ),
        )
        .limit(3)
        .all()
    )
    anuncios = (
        db.query(AnuncioPlataforma.titulo)
        .filter(
            AnuncioPlataforma.status == "ativo",
            AnuncioPlataforma.titulo.ilike(pattern),
        )
        .limit(limit)
        .all()
    )
    categorias = (
        db.query(CategoriaPlataforma.nome)
        .filter(
            CategoriaPlataforma.ativa.is_(True),
            CategoriaPlataforma.nome.ilike(pattern),
        )
        .limit(3)
        .all()
    )

    termos_unicos = []
    vistos = set()
    for row in lojas:
        nome = (row[0] or "").strip()
        if not nome:
            continue
        lower = nome.lower()
        if lower not in vistos:
            vistos.add(lower)
            termos_unicos.append(nome)
    for row in categorias:
        t = (row[0] or "").strip()
        if not t:
            continue
        lower = t.lower()
        if lower not in vistos:
            vistos.add(lower)
            termos_unicos.append(t)
    for row in anuncios:
        t = (row[0] or "").strip()
        if not t:
            continue
        lower = t.lower()
        if lower not in vistos:
            vistos.add(lower)
            termos_unicos.append(t)
    return termos_unicos[:limit]


def termos_populares(db: Session, limit: int = 10) -> List[dict]:
    rows = (
        db.query(TermoBuscado)
        .order_by(TermoBuscado.contagem.desc())
        .limit(limit)
        .all()
    )
    return [{"termo": r.termo, "contagem": r.contagem} for r in rows]


def registrar_termo(db: Session, termo: str) -> None:
    """Registra termo usando INSERT ... ON CONFLICT para atomicidade."""
    termo_lower = termo.strip().lower()[:255]
    if not termo_lower or len(termo_lower) < 3:
        return
    try:
        db.execute(
            text(
                "INSERT INTO termos_buscados (termo, contagem) "
                "VALUES (:termo, 1) "
                "ON CONFLICT (termo) DO UPDATE SET contagem = termos_buscados.contagem + 1"
            ),
            {"termo": termo_lower},
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Falha ao registrar termo de busca: %s", termo_lower)
