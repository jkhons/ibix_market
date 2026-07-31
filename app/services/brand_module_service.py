# PDV Ibix — Módulos ofertados por marca
from __future__ import annotations

from typing import FrozenSet

from sqlalchemy.orm import Session

from app.models.brand_module import BrandModule
from app.models.module import Module


def fetch_brand_module_slugs_from_db(db: Session, brand_id: int) -> FrozenSet[str]:
    rows = (
        db.query(Module.slug)
        .join(BrandModule, BrandModule.module_id == Module.id)
        .filter(
            BrandModule.brand_id == brand_id,
            Module.ativo.is_(True),
        )
        .all()
    )
    return frozenset(r[0] for r in rows if r[0])
