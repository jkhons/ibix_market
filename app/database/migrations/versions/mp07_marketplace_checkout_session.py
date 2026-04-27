"""Sessão de checkout multi-loja (um pagamento, N pedidos).

Revision ID: mp07_checkout_session
Revises: inf01_influencer_base
Create Date: 2026-03-31

"""
import sqlalchemy as sa
from alembic import op

revision = "mp07_checkout_session"
down_revision = "inf01_influencer_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_checkout_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("total_agregado", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketplace_checkout_sessions_uuid", "marketplace_checkout_sessions", ["uuid"], unique=True)
    op.create_index("ix_marketplace_checkout_sessions_idempotency_key", "marketplace_checkout_sessions", ["idempotency_key"])

    op.create_table(
        "marketplace_checkout_session_pedidos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["session_id"], ["marketplace_checkout_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos_marketplace.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "pedido_id", name="uq_session_pedido"),
    )
    op.create_index("ix_mcsp_session_id", "marketplace_checkout_session_pedidos", ["session_id"])
    op.create_index("ix_mcsp_pedido_id", "marketplace_checkout_session_pedidos", ["pedido_id"])

    op.add_column(
        "payment_transactions",
        sa.Column("checkout_session_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_payment_transactions_checkout_session",
        "payment_transactions",
        "marketplace_checkout_sessions",
        ["checkout_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_payment_transactions_checkout_session_id", "payment_transactions", ["checkout_session_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_transactions_checkout_session_id", table_name="payment_transactions")
    op.drop_constraint("fk_payment_transactions_checkout_session", "payment_transactions", type_="foreignkey")
    op.drop_column("payment_transactions", "checkout_session_id")

    op.drop_index("ix_mcsp_pedido_id", table_name="marketplace_checkout_session_pedidos")
    op.drop_index("ix_mcsp_session_id", table_name="marketplace_checkout_session_pedidos")
    op.drop_table("marketplace_checkout_session_pedidos")

    op.drop_index("ix_marketplace_checkout_sessions_idempotency_key", table_name="marketplace_checkout_sessions")
    op.drop_index("ix_marketplace_checkout_sessions_uuid", table_name="marketplace_checkout_sessions")
    op.drop_table("marketplace_checkout_sessions")
