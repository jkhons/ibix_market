"""Adicionar produto_cliente_id em notas_fiscais_itens, cupons_fiscais_itens, ordem_servico_itens.

Revision ID: pc04_add_pcid
Revises: pc03_mapear
Create Date: 2026-03-03

"""
import sqlalchemy as sa
from alembic import op

revision = "pc04_add_pcid"
down_revision = "pc03_mapear"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notas_fiscais_itens",
        sa.Column("produto_cliente_id", sa.Integer(), sa.ForeignKey("produtos_cliente.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "cupons_fiscais_itens",
        sa.Column("produto_cliente_id", sa.Integer(), sa.ForeignKey("produtos_cliente.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "ordem_servico_itens",
        sa.Column("produto_cliente_id", sa.Integer(), sa.ForeignKey("produtos_cliente.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ordem_servico_itens", "produto_cliente_id")
    op.drop_column("cupons_fiscais_itens", "produto_cliente_id")
    op.drop_column("notas_fiscais_itens", "produto_cliente_id")
