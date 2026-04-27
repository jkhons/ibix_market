"""add geocoding_precision em clientes

Revision ID: aa78cc680p7z3
Revises: mp08_pedido_comprador_registered_backfill
Create Date: 2026-04-27

Auditoria da precisao da geocodificacao da loja (rooftop, range_interpolated, locality, etc.).
Usado pelo fluxo de "perto de voce" para nao depender do centroide da cidade.
"""
import sqlalchemy as sa
from alembic import op

revision = "aa78cc680p7z3"
down_revision = "mp08_pedido_comprador_registered_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clientes",
        sa.Column(
            "geocoding_precision",
            sa.String(length=20),
            nullable=True,
            comment="Precisao da geocodificacao da loja (rooftop|range_interpolated|locality|manual).",
        ),
    )
    op.create_index(
        "idx_clientes_geocoding_precision",
        "clientes",
        ["geocoding_precision"],
    )


def downgrade() -> None:
    op.drop_index("idx_clientes_geocoding_precision", table_name="clientes")
    op.drop_column("clientes", "geocoding_precision")
