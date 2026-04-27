"""Pedidos marketplace: aceite da Política de Privacidade (snapshot no checkout).

Revision ID: mk04_politica
Revises: mk03_guest
Create Date: 2026-03-10

- pedidos_marketplace.aceite_politica_privacidade_snapshot (Boolean, default true para retrocompatibilidade).
"""
import sqlalchemy as sa
from alembic import op

revision = "mk04_politica"
down_revision = "mk03_guest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pedidos_marketplace",
        sa.Column("aceite_politica_privacidade_snapshot", sa.Boolean(), server_default="true", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("pedidos_marketplace", "aceite_politica_privacidade_snapshot")
