"""add access_log (classificação de visitantes)

Revision ID: kk00mm136b6
Revises: jj99ll025b5
Create Date: 2026-02-20

Tabela access_log: registro de acessos com classificação HUMANO/BOT/CLOUD (IP + User-Agent).
"""
import sqlalchemy as sa
from alembic import op

revision = "kk00mm136b6"
down_revision = "jj99ll025b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "access_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("tipo_visitante", sa.String(10), nullable=False),
        sa.Column("path", sa.String(512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        comment="Log de acessos com classificação de visitante (HUMANO/BOT/CLOUD)",
    )
    op.create_index("ix_access_log_id", "access_log", ["id"])
    op.create_index("ix_access_log_created_at", "access_log", ["created_at"])
    op.create_index("ix_access_log_tipo_visitante", "access_log", ["tipo_visitante"])


def downgrade() -> None:
    op.drop_index("ix_access_log_tipo_visitante", "access_log")
    op.drop_index("ix_access_log_created_at", "access_log")
    op.drop_index("ix_access_log_id", "access_log")
    op.drop_table("access_log")
