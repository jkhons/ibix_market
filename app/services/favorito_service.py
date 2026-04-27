# PDV Ibix - Service para favoritos (wishlist) do consumidor
import json
import logging
from typing import List, Tuple

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.anuncio_plataforma import AnuncioPlataforma
from app.models.consumidor_favorito import ConsumidorFavorito

logger = logging.getLogger(__name__)


def listar_favoritos(
    db: Session,
    consumidor_id: int,
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[dict], int]:
    total = (
        db.query(func.count(ConsumidorFavorito.id))
        .filter(ConsumidorFavorito.consumidor_id == consumidor_id)
        .scalar()
    )
    rows = (
        db.query(ConsumidorFavorito, AnuncioPlataforma)
        .join(AnuncioPlataforma, ConsumidorFavorito.anuncio_id == AnuncioPlataforma.id)
        .filter(ConsumidorFavorito.consumidor_id == consumidor_id)
        .order_by(ConsumidorFavorito.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = []
    for fav, anuncio in rows:
        imagens_raw = anuncio.imagens or ""
        imagem_capa = None
        if imagens_raw:
            try:
                imgs = json.loads(imagens_raw) if isinstance(imagens_raw, str) else imagens_raw
                if isinstance(imgs, list) and imgs:
                    imagem_capa = imgs[0] if isinstance(imgs[0], str) else imgs[0].get("url")
            except (json.JSONDecodeError, TypeError, AttributeError):
                logger.warning("Imagem inválida no anúncio %s", anuncio.id)
        items.append({
            "id": fav.id,
            "anuncio_id": fav.anuncio_id,
            "created_at": fav.created_at,
            "anuncio": {
                "id": anuncio.id,
                "titulo": anuncio.titulo,
                "preco_original": float(anuncio.preco_original),
                "preco_promocional": float(anuncio.preco_promocional) if anuncio.preco_promocional else None,
                "imagem_capa": imagem_capa,
                "status": anuncio.status,
            },
        })
    return items, total


def adicionar_favorito(db: Session, consumidor_id: int, anuncio_id: int) -> ConsumidorFavorito:
    existing = (
        db.query(ConsumidorFavorito)
        .filter(
            ConsumidorFavorito.consumidor_id == consumidor_id,
            ConsumidorFavorito.anuncio_id == anuncio_id,
        )
        .first()
    )
    if existing:
        return existing

    anuncio = db.query(AnuncioPlataforma).filter(AnuncioPlataforma.id == anuncio_id).first()
    if not anuncio:
        raise ValueError("ANUNCIO_NOT_FOUND")

    fav = ConsumidorFavorito(consumidor_id=consumidor_id, anuncio_id=anuncio_id)
    db.add(fav)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(ConsumidorFavorito)
            .filter(
                ConsumidorFavorito.consumidor_id == consumidor_id,
                ConsumidorFavorito.anuncio_id == anuncio_id,
            )
            .first()
        )
        if existing:
            return existing
        raise
    db.refresh(fav)
    return fav


def remover_favorito(db: Session, consumidor_id: int, anuncio_id: int) -> bool:
    fav = (
        db.query(ConsumidorFavorito)
        .filter(
            ConsumidorFavorito.consumidor_id == consumidor_id,
            ConsumidorFavorito.anuncio_id == anuncio_id,
        )
        .first()
    )
    if not fav:
        return False
    db.delete(fav)
    db.commit()
    return True


def is_favorito(db: Session, consumidor_id: int, anuncio_id: int) -> bool:
    return (
        db.query(ConsumidorFavorito)
        .filter(
            ConsumidorFavorito.consumidor_id == consumidor_id,
            ConsumidorFavorito.anuncio_id == anuncio_id,
        )
        .first()
    ) is not None
