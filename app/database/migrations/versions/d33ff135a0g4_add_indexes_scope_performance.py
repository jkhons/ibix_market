"""add indexes for scope and performance (Saas.md Fase 4)

Revision ID: d33ff135a0g4
Revises: c22ee024b9f3
Create Date: 2026-02-06

"""
from alembic import op
from sqlalchemy import text

revision = "d33ff135a0g4"
down_revision = "c22ee024b9f3"
branch_labels = None
depends_on = None


def _create_index_if_not_exists(conn, table: str, name: str, *columns: str) -> None:
    # PostgreSQL
    cols = ", ".join(columns)
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols})"))


def upgrade() -> None:
    conn = op.get_bind()
    # Saas.md Fase 4: índices para filtros e JOINs
    _create_index_if_not_exists(conn, "usuarios", "idx_usuarios_role_id", "role_id")
    _create_index_if_not_exists(conn, "areas_cliente", "idx_areas_cliente_usuario_id", "usuario_id")
    _create_index_if_not_exists(conn, "areas_cliente", "idx_areas_cliente_cliente_id", "cliente_id")
    _create_index_if_not_exists(conn, "processos", "idx_processos_cliente_id", "cliente_id")
    _create_index_if_not_exists(conn, "processos", "idx_processos_tecnico_responsavel_id", "tecnico_responsavel_id")
    _create_index_if_not_exists(conn, "certificados", "idx_certificados_cliente_id", "cliente_id")


def downgrade() -> None:
    conn = op.get_bind()
    for name in [
        "idx_usuarios_role_id",
        "idx_areas_cliente_usuario_id",
        "idx_areas_cliente_cliente_id",
        "idx_processos_cliente_id",
        "idx_processos_tecnico_responsavel_id",
        "idx_certificados_cliente_id",
    ]:
        conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
