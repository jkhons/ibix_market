# PDV Ibix - Service para notificações in-app do consumidor mobile
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.consumidor_notificacao import ConsumidorNotificacao


def listar_notificacoes(
    db: Session,
    consumidor_id: int,
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[ConsumidorNotificacao], int, int]:
    base = db.query(ConsumidorNotificacao).filter(
        ConsumidorNotificacao.consumidor_id == consumidor_id
    )
    total = base.count()
    nao_lidas = base.filter(ConsumidorNotificacao.lida.is_(False)).count()
    items = (
        base.order_by(ConsumidorNotificacao.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return items, total, nao_lidas


def marcar_lidas(
    db: Session,
    consumidor_id: int,
    ids: Optional[List[int]] = None,
) -> int:
    q = db.query(ConsumidorNotificacao).filter(
        ConsumidorNotificacao.consumidor_id == consumidor_id,
        ConsumidorNotificacao.lida.is_(False),
    )
    if ids:
        q = q.filter(ConsumidorNotificacao.id.in_(ids))
    count = q.update({"lida": True}, synchronize_session=False)
    db.commit()
    return count


def criar_notificacao(
    db: Session,
    consumidor_id: int,
    tipo: str,
    titulo: str,
    mensagem: str,
    dados_json: Optional[Dict[str, Any]] = None,
) -> ConsumidorNotificacao:
    notif = ConsumidorNotificacao(
        consumidor_id=consumidor_id,
        tipo=tipo,
        titulo=titulo,
        mensagem=mensagem,
        dados_json=dados_json,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def contar_nao_lidas(db: Session, consumidor_id: int) -> int:
    return (
        db.query(func.count(ConsumidorNotificacao.id))
        .filter(
            ConsumidorNotificacao.consumidor_id == consumidor_id,
            ConsumidorNotificacao.lida.is_(False),
        )
        .scalar()
    )
