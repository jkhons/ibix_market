"""Estender produtos_cliente com campos usados no Estoque (categoria, tipo_material, etc.).

Conforme plano de migração: apenas colunas que ainda não existem em produtos_cliente.
Não adiciona cfop_padrao nem referencia (já existem).

Revision ID: pc02_estender
Revises: pc01_cfop_ref
Create Date: 2026-03-03

"""
import sqlalchemy as sa
from alembic import op

revision = "pc02_estender"
down_revision = "pc01_cfop_ref"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("produtos_cliente", sa.Column("categoria", sa.String(100), nullable=True))
    op.add_column("produtos_cliente", sa.Column("tipo_material", sa.String(50), nullable=True))
    op.add_column(
        "produtos_cliente",
        sa.Column("categoria_id", sa.Integer(), sa.ForeignKey("material_categoria.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("produtos_cliente", sa.Column("fabricante", sa.String(255), nullable=True))
    op.add_column("produtos_cliente", sa.Column("fornecedor", sa.String(255), nullable=True))
    op.add_column("produtos_cliente", sa.Column("data_validade", sa.Date(), nullable=True))
    op.add_column("produtos_cliente", sa.Column("data_fabricacao", sa.Date(), nullable=True))
    op.add_column("produtos_cliente", sa.Column("controla_estoque", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("produtos_cliente", sa.Column("quantidade_maxima", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("produtos_cliente", "quantidade_maxima")
    op.drop_column("produtos_cliente", "controla_estoque")
    op.drop_column("produtos_cliente", "data_fabricacao")
    op.drop_column("produtos_cliente", "data_validade")
    op.drop_column("produtos_cliente", "fornecedor")
    op.drop_column("produtos_cliente", "fabricante")
    op.drop_column("produtos_cliente", "categoria_id")
    op.drop_column("produtos_cliente", "tipo_material")
    op.drop_column("produtos_cliente", "categoria")
