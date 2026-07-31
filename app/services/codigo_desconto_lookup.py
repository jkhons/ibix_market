# PDV Ibix — Resolução de código promocional com tolerância a formatação (hífens, pontos)
from typing import Optional
from urllib.parse import unquote

from sqlalchemy.orm import Session, joinedload

from app.models.codigo_desconto import CodigoDesconto
from app.models.divulgador import Divulgador


def normalizar_codigo_promocional_texto(codigo: str) -> str:
    """Decode URL, strip e maiúsculas (mesma base do endpoint público de validação)."""
    if not codigo:
        return ""
    return unquote(str(codigo)).strip().upper()


def _compact_alnum(s: str) -> str:
    return "".join(c for c in (s or "").upper() if c.isalnum())


def buscar_codigo_desconto_ativo_por_entrada(
    db: Session,
    codigo_raw: str,
    *,
    eager_divulgador_usuario: bool = True,
) -> Optional[CodigoDesconto]:
    """
    Localiza código ativo mesmo quando há diferença só de máscara (ex.: 18684-556 vs 18684556).

    Ordem: match exato normalizado → match ao valor só com letras/números digitado → match pela forma
    compacta do que está gravado no banco.
    """
    codigo_norm = normalizar_codigo_promocional_texto(codigo_raw)
    if not codigo_norm:
        return None

    def base_query():
        qq = db.query(CodigoDesconto).filter(CodigoDesconto.ativo.is_(True))
        if eager_divulgador_usuario:
            qq = qq.options(joinedload(CodigoDesconto.divulgador).joinedload(Divulgador.usuario))
        return qq

    hit = base_query().filter(CodigoDesconto.codigo == codigo_norm).first()
    if hit:
        return hit

    compact_in = _compact_alnum(codigo_norm)
    if compact_in:
        hit = base_query().filter(CodigoDesconto.codigo == compact_in).first()
        if hit:
            return hit

    if compact_in:
        for row in base_query().all():
            if _compact_alnum(row.codigo or "") == compact_in:
                return row

    return None


__all__ = [
    "normalizar_codigo_promocional_texto",
    "buscar_codigo_desconto_ativo_por_entrada",
]
