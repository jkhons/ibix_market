"""Mobile: tabela consumidor_notificacoes.

Revision ID: mob03_notificacoes
Revises: mob02_favoritos
Create Date: 2026-04-13
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "mob03_notificacoes"
down_revision = "mob02_favoritos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consumidor_notificacoes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("consumidor_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("dados_json", JSONB(), nullable=True),
        sa.Column("lida", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["consumidor_id"], ["consumidores_marketplace.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_consumidor_notificacoes_consumidor_id", "consumidor_notificacoes", ["consumidor_id"])
    op.create_index("ix_consumidor_notificacoes_tipo", "consumidor_notificacoes", ["tipo"])
    op.create_index(
        "ix_consumidor_notificacoes_consumidor_lida",
        "consumidor_notificacoes",
        ["consumidor_id", "lida"],
    )


def downgrade() -> None:
    op.drop_index("ix_consumidor_notificacoes_consumidor_lida", table_name="consumidor_notificacoes")
    op.drop_index("ix_consumidor_notificacoes_tipo", table_name="consumidor_notificacoes")
    op.drop_index("ix_consumidor_notificacoes_consumidor_id", table_name="consumidor_notificacoes")
    op.drop_table("consumidor_notificacoes")
