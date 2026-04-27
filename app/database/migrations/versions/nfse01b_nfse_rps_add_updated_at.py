"""Adiciona updated_at em nfse_rps (BaseModel)

Revision ID: nfse01b_rps
Revises: nfse01_tbl
Create Date: 2026-03-02

"""
import sqlalchemy as sa
from alembic import op

revision = "nfse01b_rps"
down_revision = "nfse01_tbl"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nfse_rps",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("nfse_rps", "updated_at")
