#!/usr/bin/env python3
"""Auditoria read-only pré-migração multi-brand (Fase 3.1).

Detecta slugs de tenant duplicados potenciais entre marcas e consumidores órfãos.
Uso: .venv/bin/python scripts/audit_multibrand_pre_migration.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.database.connection import SessionLocal


def main() -> int:
    db = SessionLocal()
    exit_code = 0
    try:
        print("=== Auditoria multi-brand (read-only) ===\n")

        brands = db.execute(text("SELECT id, slug FROM brands ORDER BY id")).fetchall()
        print(f"Marcas: {len(brands)}")
        for row in brands:
            print(f"  - id={row[0]} slug={row[1]}")

        if db.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='tenants' AND column_name='brand_id'"
            )
        ).fetchone():
            dup_slugs = db.execute(
                text(
                    """
                    SELECT slug, COUNT(DISTINCT brand_id) AS marcas
                    FROM tenants
                    WHERE slug IS NOT NULL
                    GROUP BY slug
                    HAVING COUNT(DISTINCT brand_id) > 1
                    ORDER BY slug
                    LIMIT 20
                    """
                )
            ).fetchall()
            if dup_slugs:
                print("\n[AVISO] Slugs de tenant repetidos em marcas distintas (esperado após br31):")
                for slug, n in dup_slugs:
                    print(f"  - {slug!r} em {n} marcas")
            else:
                print("\n[OK] Nenhum slug de tenant repetido entre marcas distintas.")

            null_brand = db.execute(
                text("SELECT COUNT(*) FROM tenants WHERE brand_id IS NULL")
            ).scalar()
            if null_brand:
                print(f"\n[ERRO] Tenants sem brand_id: {null_brand}")
                exit_code = 1
            else:
                print("[OK] Todos os tenants têm brand_id.")
        else:
            global_dupes = db.execute(
                text(
                    """
                    SELECT slug, COUNT(*) AS n
                    FROM tenants
                    WHERE slug IS NOT NULL
                    GROUP BY slug
                    HAVING COUNT(*) > 1
                    LIMIT 20
                    """
                )
            ).fetchall()
            if global_dupes:
                print("\n[AVISO] Slugs globais duplicados (resolver antes de br31):")
                for slug, n in global_dupes:
                    print(f"  - {slug!r}: {n} tenants")
                exit_code = 1
            else:
                print("\n[OK] Nenhum slug global duplicado em tenants.")

        orphans = db.execute(
            text(
                """
                SELECT COUNT(*) FROM consumidores_marketplace
                WHERE tenant_id IS NULL AND deleted_at IS NULL
                """
            )
        ).scalar()
        print(f"\nConsumidores órfãos (tenant_id NULL, ativos): {orphans}")
        if orphans:
            print("  (Permitido: escopo platform-wide Ibix; br32 backfill via pedidos quando possível)")

        orphan_emails = db.execute(
            text(
                """
                SELECT LOWER(email), COUNT(*) AS n
                FROM consumidores_marketplace
                WHERE tenant_id IS NULL AND deleted_at IS NULL
                GROUP BY LOWER(email)
                HAVING COUNT(*) > 1
                LIMIT 10
                """
            )
        ).fetchall()
        if orphan_emails:
            print("[AVISO] E-mails duplicados entre consumidores órfãos:")
            for email, n in orphan_emails:
                print(f"  - {email}: {n}")

        print("\n=== Fim da auditoria ===")
        return exit_code
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
