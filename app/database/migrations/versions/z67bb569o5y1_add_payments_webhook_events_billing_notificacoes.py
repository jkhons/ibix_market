"""add payments, webhook_events, billing_notificacoes

Revision ID: z67bb569o5y1
Revises: y56aa458n4x0
Create Date: 2026-02-12

Tabelas para rastreio de pagamentos MP, idempotência de webhooks e anti-spam de notificações.
"""
import sqlalchemy as sa
from alembic import op

revision = "z67bb569o5y1"
down_revision = "y56aa458n4x0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("mp_payment_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("amount_centavos", sa.Integer(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_reference", sa.String(128), nullable=True),
        sa.Column("payer_user_id", sa.Integer(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payer_user_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("mp_payment_id", name="uq_payments_mp_payment_id"),
        comment="Pagamentos MP por assinatura (rastreio e auditoria)",
    )
    op.create_index("ix_payments_subscription_id", "payments", ["subscription_id"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_external_reference", "payments", ["external_reference"])
    op.create_index("ix_payments_subscription_status", "payments", ["subscription_id", "status"])

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="mercadopago"),
        sa.Column("event_key", sa.String(128), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "event_key", name="uq_webhook_events_provider_event_key"),
        comment="Idempotência webhook MP (provider + event_key)",
    )
    op.create_index("ix_webhook_events_provider", "webhook_events", ["provider"])
    op.create_index("ix_webhook_events_provider_received", "webhook_events", ["provider", "received_at"])

    op.create_table(
        "billing_notificacoes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(32), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canal", sa.String(20), nullable=False, server_default="email"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "tipo", name="uq_billing_notificacoes_tenant_tipo"),
        comment="Anti-spam: notificações enviadas por tenant e tipo (trial_d7, pastdue_d7, etc.)",
    )
    op.create_index("ix_billing_notificacoes_tenant_id", "billing_notificacoes", ["tenant_id"])
    op.create_index("ix_billing_notificacoes_tenant_tipo", "billing_notificacoes", ["tenant_id", "tipo"])


def downgrade() -> None:
    op.drop_index("ix_billing_notificacoes_tenant_tipo", "billing_notificacoes")
    op.drop_index("ix_billing_notificacoes_tenant_id", "billing_notificacoes")
    op.drop_table("billing_notificacoes")
    op.drop_index("ix_webhook_events_provider_received", "webhook_events")
    op.drop_index("ix_webhook_events_provider", "webhook_events")
    op.drop_table("webhook_events")
    op.drop_index("ix_payments_subscription_status", "payments")
    op.drop_index("ix_payments_external_reference", "payments")
    op.drop_index("ix_payments_status", "payments")
    op.drop_index("ix_payments_subscription_id", "payments")
    op.drop_table("payments")
