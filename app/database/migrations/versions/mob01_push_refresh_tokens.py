"""Mobile: tabelas consumidor_push_tokens e consumidor_refresh_tokens.

Revision ID: mob01_push_refresh
Revises: mp07_checkout_session
Create Date: 2026-04-13
"""
import sqlalchemy as sa
from alembic import op

revision = "mob01_push_refresh"
down_revision = "mp07_checkout_session"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consumidor_push_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("consumidor_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(512), nullable=False),
        sa.Column("plataforma", sa.String(10), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["consumidor_id"], ["consumidores_marketplace.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token", name="uq_consumidor_push_tokens_token"),
    )
    op.create_index("ix_consumidor_push_tokens_consumidor_id", "consumidor_push_tokens", ["consumidor_id"])

    op.create_table(
        "consumidor_refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("consumidor_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("device_info", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["consumidor_id"], ["consumidores_marketplace.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_consumidor_refresh_tokens_hash"),
    )
    op.create_index("ix_consumidor_refresh_tokens_consumidor_id", "consumidor_refresh_tokens", ["consumidor_id"])


def downgrade() -> None:
    op.drop_index("ix_consumidor_refresh_tokens_consumidor_id", table_name="consumidor_refresh_tokens")
    op.drop_table("consumidor_refresh_tokens")
    op.drop_index("ix_consumidor_push_tokens_consumidor_id", table_name="consumidor_push_tokens")
    op.drop_table("consumidor_push_tokens")
