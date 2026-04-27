"""Mobile: tabelas conversas_marketplace e mensagens_conversa.

Revision ID: mob07_chat
Revises: mob06_devolucoes
Create Date: 2026-04-13
"""
import sqlalchemy as sa
from alembic import op

revision = "mob07_chat"
down_revision = "mob06_devolucoes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversas_marketplace",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("consumidor_id", sa.Integer(), nullable=False),
        sa.Column("loja_id", sa.Integer(), nullable=False),
        sa.Column("anuncio_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativa"),
        sa.Column("ultima_mensagem_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["consumidor_id"], ["consumidores_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["loja_id"], ["lojas_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["anuncio_id"], ["anuncios_plataforma.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_conversas_marketplace_consumidor_id", "conversas_marketplace", ["consumidor_id"])
    op.create_index("ix_conversas_marketplace_loja_id", "conversas_marketplace", ["loja_id"])
    op.create_index("ix_conversas_consumidor_loja", "conversas_marketplace", ["consumidor_id", "loja_id"])

    op.create_table(
        "mensagens_conversa",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("conversa_id", sa.Integer(), nullable=False),
        sa.Column("remetente_tipo", sa.String(20), nullable=False),
        sa.Column("remetente_id", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=True),
        sa.Column("imagem_url", sa.String(500), nullable=True),
        sa.Column("lida", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["conversa_id"], ["conversas_marketplace.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_mensagens_conversa_conversa_id", "mensagens_conversa", ["conversa_id"])
    op.create_index("ix_mensagens_conversa_id_created", "mensagens_conversa", ["conversa_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_mensagens_conversa_id_created", table_name="mensagens_conversa")
    op.drop_index("ix_mensagens_conversa_conversa_id", table_name="mensagens_conversa")
    op.drop_table("mensagens_conversa")
    op.drop_index("ix_conversas_consumidor_loja", table_name="conversas_marketplace")
    op.drop_index("ix_conversas_marketplace_loja_id", table_name="conversas_marketplace")
    op.drop_index("ix_conversas_marketplace_consumidor_id", table_name="conversas_marketplace")
    op.drop_table("conversas_marketplace")
