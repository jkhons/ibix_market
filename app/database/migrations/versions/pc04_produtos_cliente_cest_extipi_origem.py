"""Adicionar cest, extipi, origem_mercadoria em produtos_cliente (emissão NF).

Revision ID: pc04_cest
Revises: nfe04_itens
Create Date: 2026-03-03

Produto padronizado para saída com Nota Fiscal (origem da entrada NFe).
"""
import sqlalchemy as sa
from alembic import op

revision = "pc04_cest"
down_revision = "nfe04_itens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "produtos_cliente",
        sa.Column("cest", sa.String(10), nullable=True, comment="Código Especificador da Substituição Tributária"),
    )
    op.add_column(
        "produtos_cliente",
        sa.Column("extipi", sa.String(5), nullable=True, comment="EX TIPI (emissão NF)"),
    )
    op.add_column(
        "produtos_cliente",
        sa.Column("origem_mercadoria", sa.Integer(), nullable=True, comment="Origem da mercadoria 0-8 (ICMS)"),
    )


def downgrade() -> None:
    op.drop_column("produtos_cliente", "origem_mercadoria")
    op.drop_column("produtos_cliente", "extipi")
    op.drop_column("produtos_cliente", "cest")
