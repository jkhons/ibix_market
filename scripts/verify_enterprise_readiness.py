#!/usr/bin/env python3
"""Checagens read-only de prontidão enterprise (Fase 9)."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.core.enterprise_checks import run_enterprise_startup_checks  # noqa: E402
from app.core.rls import rls_enabled  # noqa: E402


def main() -> int:
    result = run_enterprise_startup_checks(strict=False)
    exit_code = 0

    print(f"RLS_ENABLED={rls_enabled()}")
    print(f"DB_USER={os.getenv('DB_USER', 'postgres')}")
    print(f"ENV={os.getenv('ENV', '')}")

    if result["warnings"]:
        print("\nAvisos:")
        for w in result["warnings"]:
            print(f"  - {w}")

    if result["errors"]:
        print("\nErros (corrigir antes de strict):")
        for e in result["errors"]:
            print(f"  - {e}")
        exit_code = 1

    if rls_enabled() and os.getenv("DB_USER", "").strip().lower() == "postgres":
        print("\nAção: executar scripts/sql/create_pdv_app_role.sql e migrar DB_USER=pdv_app")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
