"""Social auth para consumidor marketplace (CF).

Revision ID: sc01_social_cf
Revises: mp04_modo_rep
Create Date: 2026-03-25
"""
import sqlalchemy as sa
from alembic import op

revision = "sc01_social_cf"
down_revision = "mp04_modo_rep"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "consumidores_marketplace",
        sa.Column("origem_social_provider", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "consumidores_marketplace",
        sa.Column("email_verificado", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "consumidores_marketplace",
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
    )

    op.create_table(
        "consumidor_social_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("consumidor_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("email_provider", sa.String(length=255), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("nome_provider", sa.String(length=200), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["consumidor_id"], ["consumidores_marketplace.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_consumidor_social_provider_user"),
        sa.UniqueConstraint("consumidor_id", "provider", name="uq_consumidor_social_consumidor_provider"),
    )
    op.create_index(op.f("ix_consumidor_social_identities_consumidor_id"), "consumidor_social_identities", ["consumidor_id"])
    op.create_index(op.f("ix_consumidor_social_identities_provider"), "consumidor_social_identities", ["provider"])
    op.create_index(op.f("ix_consumidor_social_identities_provider_user_id"), "consumidor_social_identities", ["provider_user_id"])

    op.create_table(
        "consumidor_social_link_pending",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("consumidor_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("email_provider", sa.String(length=255), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("nome_provider", sa.String(length=200), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_consumidor_social_link_pending_consumidor_id"), "consumidor_social_link_pending", ["consumidor_id"])
    op.create_index(op.f("ix_consumidor_social_link_pending_provider"), "consumidor_social_link_pending", ["provider"])
    op.create_index(op.f("ix_consumidor_social_link_pending_token_hash"), "consumidor_social_link_pending", ["token_hash"])
    op.create_index(op.f("ix_consumidor_social_link_pending_expires_at"), "consumidor_social_link_pending", ["expires_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_consumidor_social_link_pending_expires_at"), table_name="consumidor_social_link_pending")
    op.drop_index(op.f("ix_consumidor_social_link_pending_token_hash"), table_name="consumidor_social_link_pending")
    op.drop_index(op.f("ix_consumidor_social_link_pending_provider"), table_name="consumidor_social_link_pending")
    op.drop_index(op.f("ix_consumidor_social_link_pending_consumidor_id"), table_name="consumidor_social_link_pending")
    op.drop_table("consumidor_social_link_pending")

    op.drop_index(op.f("ix_consumidor_social_identities_provider_user_id"), table_name="consumidor_social_identities")
    op.drop_index(op.f("ix_consumidor_social_identities_provider"), table_name="consumidor_social_identities")
    op.drop_index(op.f("ix_consumidor_social_identities_consumidor_id"), table_name="consumidor_social_identities")
    op.drop_table("consumidor_social_identities")

    op.drop_column("consumidores_marketplace", "avatar_url")
    op.drop_column("consumidores_marketplace", "email_verificado")
    op.drop_column("consumidores_marketplace", "origem_social_provider")
