"""Mobile: tabelas cupons_marketplace e cupons_consumidor.

Revision ID: mob05_cupons
Revises: mob04_app_versao
Create Date: 2026-04-13
"""
import sqlalchemy as sa
from alembic import op

revision = "mob05_cupons"
down_revision = "mob04_app_versao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cupons_marketplace",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("tipo_desconto", sa.String(20), nullable=False),
        sa.Column("valor_desconto", sa.Numeric(10, 2), nullable=False),
        sa.Column("valor_minimo_pedido", sa.Numeric(10, 2), nullable=True),
        sa.Column("uso_maximo", sa.Integer(), nullable=True),
        sa.Column("uso_atual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uso_maximo_por_consumidor", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("valido_de", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valido_ate", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("loja_id", sa.Integer(), nullable=True),
        sa.Column("criado_por", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["loja_id"], ["lojas_marketplace.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("codigo", name="uq_cupons_marketplace_codigo"),
    )
    op.create_index("ix_cupons_marketplace_codigo", "cupons_marketplace", ["codigo"])
    op.create_index("ix_cupons_marketplace_loja_id", "cupons_marketplace", ["loja_id"])
    op.create_index("ix_cupons_marketplace_ativo", "cupons_marketplace", ["ativo"])

    op.create_table(
        "cupons_consumidor",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cupom_id", sa.Integer(), nullable=False),
        sa.Column("consumidor_id", sa.Integer(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=True),
        sa.Column("usado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cupom_id"], ["cupons_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["consumidor_id"], ["consumidores_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos_marketplace.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_cupons_consumidor_cupom_consumidor", "cupons_consumidor", ["cupom_id", "consumidor_id"])


def downgrade() -> None:
    op.drop_index("ix_cupons_consumidor_cupom_consumidor", table_name="cupons_consumidor")
    op.drop_table("cupons_consumidor")
    op.drop_index("ix_cupons_marketplace_ativo", table_name="cupons_marketplace")
    op.drop_index("ix_cupons_marketplace_loja_id", table_name="cupons_marketplace")
    op.drop_index("ix_cupons_marketplace_codigo", table_name="cupons_marketplace")
    op.drop_table("cupons_marketplace")
