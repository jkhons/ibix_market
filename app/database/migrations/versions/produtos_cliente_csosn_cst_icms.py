"""Adicionar csosn e cst_icms em produtos_cliente (emissão NF-e: correção no cadastro, sem normalização).

Revision ID: prod_cli_csosn
Revises: merge_fiscal_heads
Create Date: 2026-03-12

Permite preencher CSOSN/CST ICMS no cadastro do produto; o preenchimento fiscal
vem do produto, não de valor padrão.
"""
import sqlalchemy as sa
from alembic import op

revision = "prod_cli_csosn"
down_revision = "merge_fiscal_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "produtos_cliente",
        sa.Column("csosn", sa.String(5), nullable=True, comment="CSOSN (Simples Nacional) para emissão NF-e"),
    )
    op.add_column(
        "produtos_cliente",
        sa.Column("cst_icms", sa.String(5), nullable=True, comment="CST ICMS (Regime Normal) para emissão NF-e"),
    )


def downgrade() -> None:
    op.drop_column("produtos_cliente", "cst_icms")
    op.drop_column("produtos_cliente", "csosn")
