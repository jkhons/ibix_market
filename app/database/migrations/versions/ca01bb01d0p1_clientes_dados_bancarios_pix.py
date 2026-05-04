"""add dados bancarios e pix em clientes (cadastro CA)

Revision ID: ca01bb01d0p1
Revises: b11de913c8a2
Create Date: 2026-04-30

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "ca01bb01d0p1"
down_revision = "b11de913c8a2"
branch_labels = None
depends_on = None


def _table_exists(conn, name: str) -> bool:
    r = conn.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :t"),
        {"t": name},
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, "clientes"):
        return

    op.add_column("clientes", sa.Column("banco_nome", sa.String(length=100), nullable=True))
    op.add_column("clientes", sa.Column("banco_codigo", sa.String(length=10), nullable=True))
    op.add_column("clientes", sa.Column("agencia", sa.String(length=20), nullable=True))
    op.add_column("clientes", sa.Column("conta", sa.String(length=30), nullable=True))
    op.add_column("clientes", sa.Column("tipo_conta", sa.String(length=20), nullable=True))
    op.add_column("clientes", sa.Column("pix_chave", sa.String(length=120), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, "clientes"):
        return

    op.drop_column("clientes", "pix_chave")
    op.drop_column("clientes", "tipo_conta")
    op.drop_column("clientes", "conta")
    op.drop_column("clientes", "agencia")
    op.drop_column("clientes", "banco_codigo")
    op.drop_column("clientes", "banco_nome")

