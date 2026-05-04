#!/usr/bin/env python3
"""Remove linha órfã mt01_marketplace_taxa_regras em alembic_version quando nt01_notifications também está lá.

O Alembic passa a erro:
  RevisionError: nt01_notifications overlaps with mt01_marketplace_taxa_regras
quando há três heads efetivos (ex.: ca01 + mt01 + nt01). Como nt01 já revisa mt01, a linha de
mt01 como revisão atual é redundante e deve ser removida.

Uso (raiz do repo, com .venv ativo):
  python scripts/fix_alembic_mt01_nt01_overlap.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.database.connection import get_database_url


def main() -> None:
    engine = create_engine(get_database_url())
    with engine.begin() as conn:
        before = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY 1")).fetchall()
        print("Antes:", before)
        result = conn.execute(
            text(
                """
                DELETE FROM alembic_version
                WHERE version_num = 'mt01_marketplace_taxa_regras'
                  AND EXISTS (
                      SELECT 1 FROM alembic_version WHERE version_num = 'nt01_notifications'
                  )
                """
            )
        )
        print("Removidas:", result.rowcount, "linha(s) mt01 (redundante com nt01).")
        after = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY 1")).fetchall()
        print("Depois:", after)


if __name__ == "__main__":
    main()
