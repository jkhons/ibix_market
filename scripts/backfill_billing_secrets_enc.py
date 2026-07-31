#!/usr/bin/env python3
"""Backfill idempotente: cifrar segredos billing legados em configuracoes (enc:v1:)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.billing_secrets import BILLING_SECRET_KEYS, SECRET_PREFIX, encrypt_stored_secret
from app.database.connection import open_db_session
from app.models import Configuracao


def main() -> int:
    db = open_db_session(bypass_rls=True)
    updated = 0
    skipped = 0
    try:
        rows = (
            db.query(Configuracao)
            .filter(Configuracao.chave.in_(tuple(BILLING_SECRET_KEYS)))
            .all()
        )
        for row in rows:
            raw = (row.valor or "").strip()
            if not raw or raw.startswith(SECRET_PREFIX):
                skipped += 1
                continue
            row.valor = encrypt_stored_secret(raw)
            updated += 1
        db.commit()
        print(f"billing secrets: {updated} cifrados, {skipped} já cifrados ou vazios")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
