"""Idempotency key em pedidos_marketplace (checkout).

Revision ID: mp03_idempotency
Revises: mp02_refunds_billing
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op

revision = "mp03_idempotency"
down_revision = "mp02_refunds_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pedidos_marketplace",
        sa.Column("idempotency_key", sa.String(128), nullable=True, comment="Chave de idempotência do checkout"),
    )
    op.create_index("ix_pedidos_marketplace_idempotency_key", "pedidos_marketplace", ["idempotency_key"])
    op.create_index(
        "ix_pedidos_marketplace_tenant_loja_idempotency",
        "pedidos_marketplace",
        ["tenant_id", "loja_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_pedidos_marketplace_tenant_loja_idempotency", "pedidos_marketplace")
    op.drop_index("ix_pedidos_marketplace_idempotency_key", "pedidos_marketplace")
    op.drop_column("pedidos_marketplace", "idempotency_key")
