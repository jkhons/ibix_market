"""add subscriptions (billing) for trial/ativa/bloqueada

Revision ID: y56aa458n4x0
Revises: x34zz247m3v9
Create Date: 2026-02-12

Assinatura de cobrança por tenant (SubscriptionBilling).
"""
import sqlalchemy as sa
from alembic import op

revision = "y56aa458n4x0"
down_revision = "x34zz247m3v9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("plano_codigo", sa.String(50), nullable=False, server_default="pdv_solumatica_490"),
        sa.Column("valor_mensal_centavos", sa.Integer(), nullable=False, server_default="49000"),
        sa.Column("status", sa.String(20), nullable=False, server_default="trial"),
        sa.Column("grace_days", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("next_charge_at", sa.Date(), nullable=True),
        sa.Column("last_paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mp_preference_id", sa.String(64), nullable=True),
        sa.Column("last_payer_user_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_payer_user_id"], ["usuarios.id"], ondelete="SET NULL"),
        comment="Assinatura de cobrança por tenant (billing)",
    )
    op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_tenant_status", "subscriptions", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_subscriptions_tenant_status", "subscriptions")
    op.drop_index("ix_subscriptions_status", "subscriptions")
    op.drop_index("ix_subscriptions_tenant_id", "subscriptions")
    op.drop_table("subscriptions")
