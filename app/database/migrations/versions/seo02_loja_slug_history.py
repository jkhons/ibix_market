"""Tabela de histórico de slug da loja

Revision ID: seo02_loja_slug_history
Revises: seo01_loja_campos_seo
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "seo02_loja_slug_history"
down_revision = "seo01_loja_campos_seo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loja_slug_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("loja_id", sa.Integer(), nullable=False),
        sa.Column("slug_antigo", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["loja_id"], ["lojas_marketplace.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug_antigo", name="uq_loja_slug_history_slug_antigo"),
    )
    op.create_index("ix_loja_slug_history_loja_id", "loja_slug_history", ["loja_id"], unique=False)
    op.create_index("ix_loja_slug_history_slug_antigo", "loja_slug_history", ["slug_antigo"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_loja_slug_history_slug_antigo", table_name="loja_slug_history")
    op.drop_index("ix_loja_slug_history_loja_id", table_name="loja_slug_history")
    op.drop_table("loja_slug_history")
