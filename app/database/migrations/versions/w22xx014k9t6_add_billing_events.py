"""add billing_events (webhook idempotencia)

Revision ID: w22xx014k9t6
Revises: v11ww903j8s5
Create Date: 2026-02-08

E4.1/E5.4: billing_events para webhook assinado + idempotencia.
"""
import sqlalchemy as sa
from alembic import op

revision = "w22xx014k9t6"
down_revision = "v11ww903j8s5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("webhook_id", sa.String(128), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("assinatura_recebida", sa.String(256), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="recebido"),
        sa.Column("erro_detalhe", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("webhook_id", name="uq_billing_events_webhook_id"),
        comment="Webhook billing: idempotencia + assinatura",
    )
    op.create_index("ix_billing_events_id", "billing_events", ["id"])
    op.create_index("ix_billing_events_webhook_id", "billing_events", ["webhook_id"])
    op.create_index("ix_billing_events_status", "billing_events", ["status"])
    op.create_index("ix_billing_events_status_created", "billing_events", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_billing_events_status_created", "billing_events")
    op.drop_index("ix_billing_events_status", "billing_events")
    op.drop_index("ix_billing_events_webhook_id", "billing_events")
    op.drop_index("ix_billing_events_id", "billing_events")
    op.drop_table("billing_events")
