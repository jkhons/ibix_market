"""add whatsapp_webhook_events (histórico webhook WhatsApp + X-Hub-Signature-256)

Revision ID: h88ii802j9k4
Revises: a78dd581k6l3
Create Date: 2026-02-26

Persistência de eventos do webhook WhatsApp (Meta) e validação X-Hub-Signature-256.
"""
import sqlalchemy as sa
from alembic import op

revision = "h88ii802j9k4"
down_revision = "a78dd581k6l3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_webhook_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("tipo_evento", sa.String(64), nullable=True),
        sa.Column("from_phone", sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        comment="Histórico webhook WhatsApp (Meta)",
    )
    op.create_index("ix_whatsapp_webhook_events_id", "whatsapp_webhook_events", ["id"])
    op.create_index("ix_whatsapp_webhook_events_tipo_evento", "whatsapp_webhook_events", ["tipo_evento"])
    op.create_index("ix_whatsapp_webhook_events_from_phone", "whatsapp_webhook_events", ["from_phone"])
    op.create_index("ix_whatsapp_webhook_events_created_at", "whatsapp_webhook_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_whatsapp_webhook_events_created_at", "whatsapp_webhook_events")
    op.drop_index("ix_whatsapp_webhook_events_from_phone", "whatsapp_webhook_events")
    op.drop_index("ix_whatsapp_webhook_events_tipo_evento", "whatsapp_webhook_events")
    op.drop_index("ix_whatsapp_webhook_events_id", "whatsapp_webhook_events")
    op.drop_table("whatsapp_webhook_events")
