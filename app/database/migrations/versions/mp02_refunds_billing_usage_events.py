"""Refunds e billing_usage_events (Fase A4, A5).

Revision ID: mp02_refunds_billing
Revises: mp01_payments
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op

revision = "mp02_refunds_billing"
down_revision = "mp01_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refunds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("payment_transaction_id", sa.Integer(), nullable=False),
        sa.Column("provider_code", sa.String(50), nullable=False),
        sa.Column("provider_refund_id", sa.String(200), nullable=True),
        sa.Column("refund_type", sa.String(20), nullable=False, server_default="full", comment="full, partial"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["payment_transaction_id"], ["payment_transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_refunds_payment_transaction_id", "refunds", ["payment_transaction_id"])
    op.create_index("ix_refunds_status", "refunds", ["status"])

    op.create_table(
        "billing_usage_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("loja_id", sa.Integer(), nullable=True),
        sa.Column("pedido_id", sa.Integer(), nullable=True),
        sa.Column("payment_transaction_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("provider_payment_id", sa.String(200), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("item_count_billable", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("gross_amount_billable", sa.Numeric(12, 2), nullable=True),
        sa.Column("percentage_base_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_reversal", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("source_refund_id", sa.Integer(), nullable=True),
        sa.Column("counted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["loja_id"], ["lojas_marketplace.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos_marketplace.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_transaction_id"], ["payment_transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_refund_id"], ["refunds.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_billing_usage_events_cliente_id", "billing_usage_events", ["cliente_id"])
    op.create_index("ix_billing_usage_events_payment_transaction_id", "billing_usage_events", ["payment_transaction_id"])
    op.create_index("ix_billing_usage_events_event_type", "billing_usage_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_billing_usage_events_event_type", "billing_usage_events")
    op.drop_index("ix_billing_usage_events_payment_transaction_id", "billing_usage_events")
    op.drop_index("ix_billing_usage_events_cliente_id", "billing_usage_events")
    op.drop_table("billing_usage_events")
    op.drop_index("ix_refunds_status", "refunds")
    op.drop_index("ix_refunds_payment_transaction_id", "refunds")
    op.drop_table("refunds")
