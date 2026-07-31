# PDV Ibix - Cobertura geográfica do marketplace definida pela plataforma (Superadmin)
from __future__ import annotations

from typing import Optional, Sequence, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import PlataformaCidadeCobertura


def _normalize_cidade_uf(cidade: Optional[str], uf: Optional[str]) -> Tuple[str, str]:
    c = (cidade or "").strip()
    u = (uf or "").strip().upper()[:2]
    return c, u


def plataforma_cobertura_ativa(db: Session) -> bool:
    """Retorna True se há ao menos uma cidade ativa configurada pela plataforma."""
    exists = (
        db.query(PlataformaCidadeCobertura.id)
        .filter(PlataformaCidadeCobertura.ativo.is_(True))
        .limit(1)
        .first()
    )
    return exists is not None


def cidade_uf_na_cobertura_plataforma(db: Session, cidade: Optional[str], uf: Optional[str]) -> bool:
    """True se cidade/UF existe em cobertura ativa (normalização lowercase na cidade)."""
    c_raw, uf_raw = _normalize_cidade_uf(cidade, uf)
    if not c_raw or not uf_raw or len(uf_raw) != 2:
        return False
    cid = db.query(PlataformaCidadeCobertura).filter(
        func.lower(PlataformaCidadeCobertura.cidade) == c_raw.lower(),
        func.upper(PlataformaCidadeCobertura.uf) == uf_raw.upper(),
        PlataformaCidadeCobertura.ativo.is_(True),
    )
    first = cid.first()
    return first is not None


def listar_ativos(db: Session) -> Sequence[PlataformaCidadeCobertura]:
    return (
        db.query(PlataformaCidadeCobertura)
        .filter(PlataformaCidadeCobertura.ativo.is_(True))
        .order_by(PlataformaCidadeCobertura.uf, func.lower(PlataformaCidadeCobertura.cidade))
        .all()
    )


def garantir_linha_duplicada_evitada(db: Session, cidade: str, uf: str, exclude_id: Optional[int] = None) -> None:
    from fastapi import HTTPException

    c_raw, uf_raw = _normalize_cidade_uf(cidade, uf)
    q = db.query(PlataformaCidadeCobertura).filter(
        func.lower(PlataformaCidadeCobertura.cidade) == c_raw.lower(),
        func.upper(PlataformaCidadeCobertura.uf) == uf_raw.upper(),
    )
    if exclude_id is not None:
        q = q.filter(PlataformaCidadeCobertura.id != exclude_id)
    if q.first() is not None:
        raise HTTPException(status_code=409, detail=f"Cidade já cadastrada na cobertura da plataforma: {c_raw}-{uf_raw}")


def validar_areas_loja_na_cobertura(
    db: Session,
    cidade_nova: Optional[str],
    uf_nova: Optional[str],
) -> None:
    """Se a plataforma tem cobertura ativa: criar/atualizar área de loja só em cidade listada."""
    if not plataforma_cobertura_ativa(db):
        return
    from fastapi import HTTPException

    c_raw, uf_raw = _normalize_cidade_uf(cidade_nova, uf_nova)
    if not c_raw or not uf_raw:
        raise HTTPException(status_code=400, detail="Cidade e UF obrigatórios para esta plataforma")
    if not cidade_uf_na_cobertura_plataforma(db, c_raw, uf_raw):
        raise HTTPException(
            status_code=400,
            detail="Esta cidade não está autorizada pela plataforma. Cadastre em Regiões atendidas (plataforma) antes de vincular taxa por loja.",
        )
