"""Mobile: tabela consumidor_consentimentos (LGPD).

Revision ID: mob08_lgpd
Revises: mob07_chat
Create Date: 2026-04-13
"""
import sqlalchemy as sa
from alembic import op

revision = "mob08_lgpd"
down_revision = "mob07_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consumidor_consentimentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("consumidor_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("aceito", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["consumidor_id"], ["consumidores_marketplace.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("consumidor_id", "tipo", name="uq_consumidor_consentimentos_tipo"),
    )
    op.create_index("ix_consumidor_consentimentos_consumidor_id", "consumidor_consentimentos", ["consumidor_id"])


def downgrade() -> None:
    op.drop_index("ix_consumidor_consentimentos_consumidor_id", table_name="consumidor_consentimentos")
    op.drop_table("consumidor_consentimentos")
