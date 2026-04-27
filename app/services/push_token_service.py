# PDV Ibix - Service para gerenciamento de push tokens (FCM)
from typing import Optional

from sqlalchemy.orm import Session

from app.models.consumidor_push_token import ConsumidorPushToken


def registrar_push_token(
    db: Session,
    consumidor_id: int,
    token: str,
    plataforma: str,
    device_id: Optional[str] = None,
) -> ConsumidorPushToken:
    existing = (
        db.query(ConsumidorPushToken)
        .filter(ConsumidorPushToken.token == token)
        .first()
    )
    if existing:
        if existing.consumidor_id != consumidor_id:
            existing.consumidor_id = consumidor_id
        existing.plataforma = plataforma
        existing.device_id = device_id
        existing.ativo = True
        db.commit()
        db.refresh(existing)
        return existing

    novo = ConsumidorPushToken(
        consumidor_id=consumidor_id,
        token=token,
        plataforma=plataforma,
        device_id=device_id,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


def remover_push_token(db: Session, consumidor_id: int, token: str) -> bool:
    row = (
        db.query(ConsumidorPushToken)
        .filter(
            ConsumidorPushToken.consumidor_id == consumidor_id,
            ConsumidorPushToken.token == token,
        )
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def desativar_push_token(db: Session, token: str) -> None:
    """Desativa um token que o FCM reportou como inválido."""
    row = db.query(ConsumidorPushToken).filter(ConsumidorPushToken.token == token).first()
    if row:
        row.ativo = False
        db.commit()
