#!/usr/bin/env python3
"""Verifica políticas RLS ativas (Fase 6). Uso: .venv/bin/python scripts/verify_rls_policies.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.database.connection import open_db_session


def main() -> int:
    db = open_db_session(bypass_rls=True)
    code = 0
    try:
        print("=== Verificação RLS (Fase 6) ===\n")
        policies = db.execute(
            text(
                """
                SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
                FROM pg_policies
                WHERE schemaname = 'public'
                ORDER BY tablename, policyname
                """
            )
        ).fetchall()
        if not policies:
            print("[AVISO] Nenhuma política RLS em public. Migração br35 aplicada?")
            return 1

        print(f"Políticas encontradas: {len(policies)}")
        for row in policies[:30]:
            print(f"  - {row[1]}.{row[2]}")
        if len(policies) > 30:
            print(f"  ... (+{len(policies) - 30} políticas)")

        rls_tables = db.execute(
            text(
                """
                SELECT c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                  AND c.relrowsecurity = true
                ORDER BY c.relname
                """
            )
        ).fetchall()
        print(f"\nTabelas com RLS habilitado: {len(rls_tables)}")

        null_brand = db.execute(text("SELECT COUNT(*) FROM tenants WHERE brand_id IS NULL")).scalar()
        if null_brand:
            print(f"\n[ERRO] Tenants sem brand_id: {null_brand}")
            code = 1
        else:
            print("\n[OK] Todos os tenants têm brand_id (backfill Ibix).")

        tenants_policy = any(p[1] == "tenants" and "rls_tenants_scope" in (p[2] or "") for p in policies)
        if not tenants_policy:
            print("[ERRO] Política rls_tenants_scope ausente.")
            code = 1
        else:
            print("[OK] Política tenants por brand/tenant presente.")

    finally:
        db.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
