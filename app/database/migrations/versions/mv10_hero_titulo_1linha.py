"""Loja marketplace: opção hero título em uma linha (ajuste automático).

Revision ID: mv10_hero_titulo_1linha
Revises: mv09_mv_card_cliente_ids_ca
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "mv10_hero_titulo_1linha"
down_revision = "mv09_mv_card_cliente_ids_ca"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lojas_marketplace",
        sa.Column(
            "vitrine_hero_titulo_uma_linha",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("lojas_marketplace", "vitrine_hero_titulo_uma_linha")
