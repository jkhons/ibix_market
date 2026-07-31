"""Multi-brand Fase 6: Row-Level Security PostgreSQL por tenant_id / brand_id.

Revision ID: br35_rls_policies
Revises: br34_lgpd_fase4
Create Date: 2026-06-18

Pré-requisitos operacionais: backup completo + PITR verificado (scripts/backup_pre_rls.sh).
Ativar na app: RLS_ENABLED=true após aplicar esta migração.
"""
from alembic import op
import sqlalchemy as sa

from app.core.rls import RLS_SKIP_TENANT_TABLES, RLS_TENANT_POLICY, RLS_TENANTS_BRAND_POLICY

revision = "br35_rls_policies"
down_revision = "br34_lgpd_fase4"
branch_labels = None
depends_on = None


def _tenant_id_tables(conn) -> list[str]:
    rows = conn.execute(
        sa.text(
            """
            SELECT DISTINCT c.table_name
            FROM information_schema.columns c
            JOIN information_schema.tables t
              ON t.table_schema = c.table_schema AND t.table_name = c.table_name
            WHERE c.table_schema = 'public'
              AND c.column_name = 'tenant_id'
              AND t.table_type = 'BASE TABLE'
            ORDER BY c.table_name
            """
        )
    ).fetchall()
    return [r[0] for r in rows if r[0] not in RLS_SKIP_TENANT_TABLES]


def upgrade() -> None:
    conn = op.get_bind()

    # Garantir backfill brand_id (idempotente; br31 já fez)
    ibix_id = conn.execute(sa.text("SELECT id FROM brands WHERE slug = 'ibix' LIMIT 1")).scalar()
    if ibix_id:
        conn.execute(
            sa.text("UPDATE tenants SET brand_id = :bid WHERE brand_id IS NULL"),
            {"bid": ibix_id},
        )

    for table in _tenant_id_tables(conn):
        conn.execute(sa.text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
        conn.execute(sa.text(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY'))
        conn.execute(sa.text(f'DROP POLICY IF EXISTS rls_{table}_tenant ON "{table}"'))
        conn.execute(sa.text(RLS_TENANT_POLICY.format(table=table)))

    conn.execute(sa.text("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE tenants FORCE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS rls_tenants_scope ON tenants"))
    conn.execute(sa.text(RLS_TENANTS_BRAND_POLICY))


def downgrade() -> None:
    conn = op.get_bind()

    for table in _tenant_id_tables(conn):
        conn.execute(sa.text(f'DROP POLICY IF EXISTS rls_{table}_tenant ON "{table}"'))
        conn.execute(sa.text(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY'))

    conn.execute(sa.text("DROP POLICY IF EXISTS rls_tenants_scope ON tenants"))
    conn.execute(sa.text("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY"))
