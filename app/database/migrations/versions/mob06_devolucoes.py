"""Mobile: tabelas motivos_cancelamento (com seed) e devolucoes_marketplace.

Revision ID: mob06_devolucoes
Revises: mob05_cupons
Create Date: 2026-04-13
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "mob06_devolucoes"
down_revision = "mob05_cupons"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "motivos_cancelamento",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("descricao", sa.String(255), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_motivos_cancelamento_tipo_ativo", "motivos_cancelamento", ["tipo", "ativo"])

    op.execute(
        "INSERT INTO motivos_cancelamento (descricao, tipo, ordem) VALUES "
        "('Encontrei preço melhor', 'cancelamento', 1), "
        "('Desisti da compra', 'cancelamento', 2), "
        "('Tempo de entrega longo', 'cancelamento', 3), "
        "('Outro', 'cancelamento', 99), "
        "('Produto diferente do anunciado', 'devolucao', 1), "
        "('Produto com defeito', 'devolucao', 2), "
        "('Produto danificado na entrega', 'devolucao', 3), "
        "('Não era o que esperava', 'devolucao', 4), "
        "('Outro', 'devolucao', 99)"
    )

    op.create_table(
        "devolucoes_marketplace",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("consumidor_id", sa.Integer(), nullable=False),
        sa.Column("motivo_id", sa.Integer(), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="aberta"),
        sa.Column("fotos_json", JSONB(), nullable=True),
        sa.Column("valor_reembolso", sa.Numeric(10, 2), nullable=True),
        sa.Column("resposta_loja", sa.Text(), nullable=True),
        sa.Column("respondido_por", sa.Integer(), nullable=True),
        sa.Column("respondido_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["consumidor_id"], ["consumidores_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["motivo_id"], ["motivos_cancelamento.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_devolucoes_marketplace_pedido_id", "devolucoes_marketplace", ["pedido_id"])
    op.create_index("ix_devolucoes_marketplace_consumidor_id", "devolucoes_marketplace", ["consumidor_id"])
    op.create_index("ix_devolucoes_marketplace_status", "devolucoes_marketplace", ["status"])


def downgrade() -> None:
    op.drop_index("ix_devolucoes_marketplace_status", table_name="devolucoes_marketplace")
    op.drop_index("ix_devolucoes_marketplace_consumidor_id", table_name="devolucoes_marketplace")
    op.drop_index("ix_devolucoes_marketplace_pedido_id", table_name="devolucoes_marketplace")
    op.drop_table("devolucoes_marketplace")
    op.drop_index("ix_motivos_cancelamento_tipo_ativo", table_name="motivos_cancelamento")
    op.drop_table("motivos_cancelamento")
