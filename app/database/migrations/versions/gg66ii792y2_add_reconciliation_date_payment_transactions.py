"""Adiciona reconciliation_date em payment_transactions (conciliação - plano Fase 3.3).

Revision ID: gg66ii792y2
Revises: ff55hh681x1
Create Date: 2026-02-18

"""
import sqlalchemy as sa
from alembic import op

revision = "gg66ii792y2"
down_revision = "ff55hh681x1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_transactions",
        sa.Column("reconciliation_date", sa.DateTime(timezone=True), nullable=True, comment="Data em que a transação foi conciliada com extrato do provedor"),
    )


def downgrade() -> None:
    op.drop_column("payment_transactions", "reconciliation_date")
