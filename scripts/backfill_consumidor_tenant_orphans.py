#!/usr/bin/env python3
"""Backfill idempotente: consumidores_marketplace com tenant_id NULL → tenant do 1º pedido."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.database.connection import open_db_session


def main() -> int:
    db = open_db_session(bypass_rls=True)
    try:
        before = db.execute(
            text(
                """
                SELECT COUNT(*) FROM consumidores_marketplace
                WHERE tenant_id IS NULL AND deleted_at IS NULL
                """
            )
        ).scalar()

        db.execute(
            text(
                """
                UPDATE consumidores_marketplace c
                SET tenant_id = sub.cliente_id,
                    updated_at = NOW()
                FROM (
                    SELECT DISTINCT ON (p.comprador_id)
                        p.comprador_id,
                        l.cliente_id
                    FROM pedidos_marketplace p
                    JOIN lojas_marketplace l ON l.id = p.loja_id
                    WHERE p.comprador_id IS NOT NULL
                    ORDER BY p.comprador_id, p.created_at ASC
                ) sub
                WHERE c.id = sub.comprador_id
                  AND c.tenant_id IS NULL
                  AND c.deleted_at IS NULL
                """
            )
        )

        db.execute(
            text(
                """
                UPDATE enderecos_consumidor e
                SET tenant_id = c.tenant_id,
                    updated_at = NOW()
                FROM consumidores_marketplace c
                WHERE e.consumidor_id = c.id
                  AND e.tenant_id IS NULL
                  AND c.tenant_id IS NOT NULL
                """
            )
        )

        db.commit()

        after = db.execute(
            text(
                """
                SELECT COUNT(*) FROM consumidores_marketplace
                WHERE tenant_id IS NULL AND deleted_at IS NULL
                """
            )
        ).scalar()

        print(f"consumidores tenant_id NULL: {before} → {after} (platform-wide restantes OK com RLS loja bypass)")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
