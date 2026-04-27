"""Tabela password_reset_tokens para Esqueci minha senha (PDV e Loja).

Revision ID: pw01_reset
Revises: pg01_modo_repasse
Create Date: 2026-03-17

"""
import sqlalchemy as sa
from alembic import op

revision = "pw01_reset"
down_revision = "pg01_modo_repasse"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False, comment="pdv | loja"),
        sa.Column("entidade_id", sa.Integer(), nullable=False, comment="usuario_id ou consumidor_id"),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"])
    op.create_index("ix_password_reset_tokens_tipo_entidade", "password_reset_tokens", ["tipo", "entidade_id"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_tipo_entidade", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
