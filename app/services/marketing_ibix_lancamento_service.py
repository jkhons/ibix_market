# PDV Ibix — Serviço operacional Marketing Ibix Lançamento
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.marketing_campanha import MarketingCampanha
from app.models.marketing_post import MarketingPost
from app.schemas.marketing_ibix_lancamento import (
    BlocoProgresso,
    MarketingCampanhaPatch,
    MarketingCampanhaResumo,
    MarketingPostOut,
    MarketingPostPatch,
)

CAMPANHA_SLUG = "ibix_market_40d"
TZ_SP = ZoneInfo("America/Sao_Paulo")


def hoje_sp() -> date:
    return datetime.now(TZ_SP).date()


def get_campanha_ativa(db: Session) -> MarketingCampanha:
    row = (
        db.query(MarketingCampanha)
        .filter(MarketingCampanha.slug == CAMPANHA_SLUG)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campanha de lançamento não encontrada. Execute a migração me01.",
        )
    return row


def listar_posts(
    db: Session,
    *,
    bloco: Optional[str] = None,
    status_copy: Optional[str] = None,
    status_publicacao: Optional[str] = None,
) -> List[MarketingPost]:
    campanha = get_campanha_ativa(db)
    q = db.query(MarketingPost).filter(MarketingPost.campanha_id == campanha.id)
    if bloco:
        q = q.filter(MarketingPost.bloco == bloco)
    if status_copy:
        q = q.filter(MarketingPost.status_copy == status_copy)
    if status_publicacao:
        q = q.filter(MarketingPost.status_publicacao == status_publicacao)
    return q.order_by(MarketingPost.numero.asc()).all()


def get_post(db: Session, numero: int) -> MarketingPost:
    campanha = get_campanha_ativa(db)
    row = (
        db.query(MarketingPost)
        .filter(
            MarketingPost.campanha_id == campanha.id,
            MarketingPost.numero == numero,
        )
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {numero} não encontrado nesta campanha.",
        )
    return row


def _contar(posts: List[MarketingPost], attr: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for p in posts:
        key = getattr(p, attr)
        out[key] = out.get(key, 0) + 1
    return out


def _progresso_blocos(posts: List[MarketingPost]) -> List[BlocoProgresso]:
    result: List[BlocoProgresso] = []
    for bloco in ("A", "B", "C", "D"):
        subset = [p for p in posts if p.bloco == bloco]
        result.append(
            BlocoProgresso(
                bloco=bloco,  # type: ignore[arg-type]
                total=len(subset),
                copy_aprovado=sum(1 for p in subset if p.status_copy == "aprovado"),
                publicados_ambos=sum(1 for p in subset if p.status_publicacao == "ambos"),
            )
        )
    return result


def _post_hoje(posts: List[MarketingPost], hoje: date) -> Optional[MarketingPost]:
    for p in posts:
        if p.data_prevista == hoje:
            return p
    return None


def _proximo_pendente(posts: List[MarketingPost], hoje: date) -> Optional[MarketingPost]:
    candidatos = [
        p
        for p in posts
        if p.data_prevista >= hoje and p.status_publicacao != "ambos"
    ]
    if candidatos:
        return min(candidatos, key=lambda p: (p.data_prevista, p.numero))
    futuros = [p for p in posts if p.data_prevista > hoje]
    if futuros:
        return min(futuros, key=lambda p: (p.data_prevista, p.numero))
    return None


def post_to_out(row: MarketingPost) -> MarketingPostOut:
    data = MarketingPostOut.model_validate(row)
    tem = bool(
        (row.legenda_reels and str(row.legenda_reels).strip())
        or (row.cortes and len(row.cortes) > 0)
        or (row.roteiro_notas and str(row.roteiro_notas).strip())
    )
    return data.model_copy(update={"tem_roteiro": tem})


def build_campanha_resumo(db: Session) -> MarketingCampanhaResumo:
    campanha = get_campanha_ativa(db)
    posts = (
        db.query(MarketingPost)
        .filter(MarketingPost.campanha_id == campanha.id)
        .order_by(MarketingPost.numero.asc())
        .all()
    )
    hoje = hoje_sp()
    post_hoje = _post_hoje(posts, hoje)
    proximo = _proximo_pendente(posts, hoje)
    pre_inicio = hoje < campanha.data_inicio
    # Pré-início: montar os 3 primeiros posts do Bloco A (primeiro lote agendável).
    foco_montagem: List[int] = []
    if pre_inicio:
        foco_montagem = [p.numero for p in posts if p.bloco == "A" and p.numero <= 3]
    return MarketingCampanhaResumo(
        id=campanha.id,
        slug=campanha.slug,
        titulo=campanha.titulo,
        data_inicio=campanha.data_inicio,
        data_fim=campanha.data_fim,
        canais=campanha.canais,
        status=campanha.status,  # type: ignore[arg-type]
        proximo_passo=campanha.proximo_passo,
        formato=campanha.formato,
        tom=campanha.tom,
        linha_gancho=campanha.linha_gancho,
        frase_ancora=campanha.frase_ancora,
        linha_editorial=campanha.linha_editorial,
        ritmo_resumo=campanha.ritmo_resumo,
        politica_reuso=campanha.politica_reuso,
        updated_at=campanha.updated_at,
        totais_status_copy=_contar(posts, "status_copy"),
        totais_status_publicacao=_contar(posts, "status_publicacao"),
        progresso_blocos=_progresso_blocos(posts),
        post_hoje=post_to_out(post_hoje) if post_hoje else None,
        proximo_pendente=post_to_out(proximo) if proximo else None,
        pre_inicio=pre_inicio,
        foco_montagem=foco_montagem,
    )


def patch_post(
    db: Session,
    numero: int,
    body: MarketingPostPatch,
    user_id: int,
) -> MarketingPost:
    row = get_post(db, numero)
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo operacional informado para atualização.",
        )

    prev_pub = row.status_publicacao
    for key, value in data.items():
        setattr(row, key, value)

    new_pub = row.status_publicacao
    if prev_pub == "pendente" and new_pub != "pendente" and row.publicado_em is None:
        row.publicado_em = datetime.now(timezone.utc)
    if new_pub == "pendente":
        row.publicado_em = None

    row.updated_by_user_id = user_id
    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def patch_campanha(
    db: Session,
    body: MarketingCampanhaPatch,
) -> MarketingCampanha:
    campanha = get_campanha_ativa(db)
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo informado para atualização da campanha.",
        )
    for key, value in data.items():
        setattr(campanha, key, value)
    campanha.updated_at = datetime.now(timezone.utc)
    db.add(campanha)
    db.commit()
    db.refresh(campanha)
    return campanha
