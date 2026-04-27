"""Renomeia categoria_ids -> cliente_ids (tenants CA / clientes.id).

Revision ID: mv09_mv_card_cliente_ids_ca
Revises: mv08_ofertas_cat_flags
Create Date: 2026-03-26
"""
from alembic import op

revision = "mv09_mv_card_cliente_ids_ca"
down_revision = "mv08_ofertas_cat_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE marketing_vitrine_cards RENAME COLUMN categoria_ids TO cliente_ids"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE marketing_vitrine_cards RENAME COLUMN cliente_ids TO categoria_ids"
    )
