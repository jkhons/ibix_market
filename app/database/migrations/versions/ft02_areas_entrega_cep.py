"""Criar tabela loja_areas_entrega (abrangencia por cidade)

Revision ID: ft02_areas_cep
Revises: merge_ft01_pw01
Create Date: 2026-03-17
"""
import sqlalchemy as sa
from alembic import op

revision = "ft02_areas_cep"
down_revision = "merge_ft01_pw01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loja_areas_entrega",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("loja_id", sa.Integer(), sa.ForeignKey("lojas_marketplace.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("cidade", sa.String(100), nullable=False),
        sa.Column("uf", sa.String(2), nullable=False),
        sa.Column("codigo_ibge", sa.Integer(), nullable=True),
        sa.Column("taxa_entrega", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("prazo_dias", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("loja_id", "cidade", "uf", name="uq_loja_cidade_uf"),
    )


def downgrade() -> None:
    op.drop_table("loja_areas_entrega")
