# PDV Ibix - Service para chat marketplace (consumidor ↔ loja)
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.conversa_marketplace import ConversaMarketplace
from app.models.loja_marketplace import LojaMarketplace
from app.models.mensagem_conversa import MensagemConversa

logger = logging.getLogger(__name__)


def listar_conversas_consumidor(
    db: Session,
    consumidor_id: int,
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[dict], int]:
    base = db.query(ConversaMarketplace).filter(ConversaMarketplace.consumidor_id == consumidor_id)
    total = base.count()

    ultima_msg_sub = (
        db.query(
            MensagemConversa.conversa_id,
            func.max(MensagemConversa.id).label("last_id"),
        )
        .group_by(MensagemConversa.conversa_id)
        .subquery()
    )

    nao_lidas_sub = (
        db.query(
            MensagemConversa.conversa_id,
            func.count(MensagemConversa.id).label("cnt"),
        )
        .filter(
            MensagemConversa.remetente_tipo == "loja",
            MensagemConversa.lida.is_(False),
        )
        .group_by(MensagemConversa.conversa_id)
        .subquery()
    )

    rows = (
        db.query(
            ConversaMarketplace,
            LojaMarketplace.nome_loja,
            MensagemConversa.texto.label("ultima_msg_texto"),
            func.coalesce(nao_lidas_sub.c.cnt, 0).label("nao_lidas"),
        )
        .outerjoin(LojaMarketplace, LojaMarketplace.id == ConversaMarketplace.loja_id)
        .outerjoin(ultima_msg_sub, ultima_msg_sub.c.conversa_id == ConversaMarketplace.id)
        .outerjoin(
            MensagemConversa,
            MensagemConversa.id == ultima_msg_sub.c.last_id,
        )
        .outerjoin(nao_lidas_sub, nao_lidas_sub.c.conversa_id == ConversaMarketplace.id)
        .filter(ConversaMarketplace.consumidor_id == consumidor_id)
        .order_by(ConversaMarketplace.ultima_mensagem_em.desc().nullslast())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for conversa, loja_nome, ultima_texto, nao_lidas in rows:
        items.append({
            "id": conversa.id,
            "loja_id": conversa.loja_id,
            "loja_nome": loja_nome,
            "anuncio_id": conversa.anuncio_id,
            "status": conversa.status,
            "ultima_mensagem_em": conversa.ultima_mensagem_em,
            "ultima_mensagem_texto": ultima_texto,
            "nao_lidas": nao_lidas or 0,
            "created_at": conversa.created_at,
        })
    return items, total


def iniciar_conversa(
    db: Session,
    consumidor_id: int,
    loja_id: int,
    mensagem_texto: str,
    anuncio_id: Optional[int] = None,
) -> Tuple[ConversaMarketplace, MensagemConversa]:
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == loja_id).first()
    if not loja:
        raise ValueError("LOJA_NOT_FOUND")

    existente = (
        db.query(ConversaMarketplace)
        .filter(
            ConversaMarketplace.consumidor_id == consumidor_id,
            ConversaMarketplace.loja_id == loja_id,
            ConversaMarketplace.status == "ativa",
        )
        .first()
    )
    if existente:
        conversa = existente
        if anuncio_id and not conversa.anuncio_id:
            conversa.anuncio_id = anuncio_id
    else:
        conversa = ConversaMarketplace(
            consumidor_id=consumidor_id,
            loja_id=loja_id,
            anuncio_id=anuncio_id,
        )
        db.add(conversa)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            conversa = (
                db.query(ConversaMarketplace)
                .filter(
                    ConversaMarketplace.consumidor_id == consumidor_id,
                    ConversaMarketplace.loja_id == loja_id,
                    ConversaMarketplace.status == "ativa",
                )
                .first()
            )
            if not conversa:
                raise

    msg = MensagemConversa(
        conversa_id=conversa.id,
        remetente_tipo="consumidor",
        remetente_id=consumidor_id,
        texto=mensagem_texto,
    )
    db.add(msg)
    conversa.ultima_mensagem_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conversa)
    db.refresh(msg)
    return conversa, msg


def listar_mensagens(
    db: Session,
    conversa_id: int,
    consumidor_id: int,
    before_id: Optional[int] = None,
    limit: int = 30,
) -> List[MensagemConversa]:
    conversa = db.query(ConversaMarketplace).filter(ConversaMarketplace.id == conversa_id).first()
    if not conversa or conversa.consumidor_id != consumidor_id:
        raise PermissionError("CONVERSA_NOT_OWNED")

    q = db.query(MensagemConversa).filter(MensagemConversa.conversa_id == conversa_id)
    if before_id:
        q = q.filter(MensagemConversa.id < before_id)
    return q.order_by(MensagemConversa.created_at.desc()).limit(limit).all()


def enviar_mensagem_consumidor(
    db: Session,
    conversa_id: int,
    consumidor_id: int,
    texto: Optional[str] = None,
    imagem_url: Optional[str] = None,
) -> MensagemConversa:
    conversa = db.query(ConversaMarketplace).filter(ConversaMarketplace.id == conversa_id).first()
    if not conversa or conversa.consumidor_id != consumidor_id:
        raise PermissionError("CONVERSA_NOT_OWNED")
    if not texto and not imagem_url:
        raise ValueError("MESSAGE_EMPTY")

    msg = MensagemConversa(
        conversa_id=conversa_id,
        remetente_tipo="consumidor",
        remetente_id=consumidor_id,
        texto=texto,
        imagem_url=imagem_url,
    )
    db.add(msg)
    conversa.ultima_mensagem_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)
    return msg


def marcar_lida_consumidor(db: Session, conversa_id: int, consumidor_id: int) -> int:
    conversa = db.query(ConversaMarketplace).filter(ConversaMarketplace.id == conversa_id).first()
    if not conversa or conversa.consumidor_id != consumidor_id:
        raise PermissionError("CONVERSA_NOT_OWNED")
    count = (
        db.query(MensagemConversa)
        .filter(
            MensagemConversa.conversa_id == conversa_id,
            MensagemConversa.remetente_tipo == "loja",
            MensagemConversa.lida.is_(False),
        )
        .update({"lida": True}, synchronize_session=False)
    )
    db.commit()
    return count


# ─── Lado loja (admin/vendedor) ──────────────────────────────
def listar_conversas_loja(
    db: Session,
    loja_id: int,
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[dict], int]:
    from app.models.consumidor_marketplace import ConsumidorMarketplace

    base = db.query(ConversaMarketplace).filter(ConversaMarketplace.loja_id == loja_id)
    total = base.count()

    nao_lidas_sub = (
        db.query(
            MensagemConversa.conversa_id,
            func.count(MensagemConversa.id).label("cnt"),
        )
        .filter(
            MensagemConversa.remetente_tipo == "consumidor",
            MensagemConversa.lida.is_(False),
        )
        .group_by(MensagemConversa.conversa_id)
        .subquery()
    )

    rows = (
        db.query(
            ConversaMarketplace,
            ConsumidorMarketplace.nome.label("consumidor_nome"),
            func.coalesce(nao_lidas_sub.c.cnt, 0).label("nao_lidas"),
        )
        .outerjoin(ConsumidorMarketplace, ConsumidorMarketplace.id == ConversaMarketplace.consumidor_id)
        .outerjoin(nao_lidas_sub, nao_lidas_sub.c.conversa_id == ConversaMarketplace.id)
        .filter(ConversaMarketplace.loja_id == loja_id)
        .order_by(ConversaMarketplace.ultima_mensagem_em.desc().nullslast())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for conversa, consumidor_nome, nao_lidas in rows:
        items.append({
            "id": conversa.id,
            "consumidor_id": conversa.consumidor_id,
            "consumidor_nome": consumidor_nome,
            "anuncio_id": conversa.anuncio_id,
            "status": conversa.status,
            "ultima_mensagem_em": conversa.ultima_mensagem_em,
            "nao_lidas": nao_lidas or 0,
            "created_at": conversa.created_at,
        })
    return items, total


def enviar_mensagem_loja(
    db: Session,
    conversa_id: int,
    loja_user_id: int,
    texto: Optional[str] = None,
    imagem_url: Optional[str] = None,
) -> MensagemConversa:
    conversa = db.query(ConversaMarketplace).filter(ConversaMarketplace.id == conversa_id).first()
    if not conversa:
        raise ValueError("CONVERSA_NOT_FOUND")
    if not texto and not imagem_url:
        raise ValueError("MESSAGE_EMPTY")

    msg = MensagemConversa(
        conversa_id=conversa_id,
        remetente_tipo="loja",
        remetente_id=loja_user_id,
        texto=texto,
        imagem_url=imagem_url,
    )
    db.add(msg)
    conversa.ultima_mensagem_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)
    return msg


def marcar_lida_loja(db: Session, conversa_id: int) -> int:
    count = (
        db.query(MensagemConversa)
        .filter(
            MensagemConversa.conversa_id == conversa_id,
            MensagemConversa.remetente_tipo == "consumidor",
            MensagemConversa.lida.is_(False),
        )
        .update({"lida": True}, synchronize_session=False)
    )
    db.commit()
    return count
