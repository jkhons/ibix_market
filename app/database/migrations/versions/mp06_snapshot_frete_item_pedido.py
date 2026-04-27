"""Snapshot de frete por item marketplace

Revision ID: mp06_frete_item_snapshot
Revises: mp05_frete_produto
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "mp06_frete_item_snapshot"
down_revision = "mp05_frete_produto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pedido_itens_marketplace",
        sa.Column("formato_frete_item_snapshot", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "pedido_itens_marketplace",
        sa.Column("origem_frete_item_snapshot", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "pedido_itens_marketplace",
        sa.Column("taxa_entrega_item", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pedido_itens_marketplace", "taxa_entrega_item")
    op.drop_column("pedido_itens_marketplace", "origem_frete_item_snapshot")
    op.drop_column("pedido_itens_marketplace", "formato_frete_item_snapshot")
