"""Remover tabela de mapeamento e tabela estoque.

Revision ID: pc06_drop_est
Revises: pc05_backfill
Create Date: 2026-03-03

"""
from alembic import op

revision = "pc06_drop_est"
down_revision = "pc05_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("migracao_estoque_produto_cliente_map")
    op.drop_table("estoque")


def downgrade() -> None:
    raise NotImplementedError("Recrear tabela estoque e mapa não implementado.")
