"""Adiciona regime_tributario e aliquotas_uf em empresa (campos de Estabelecimento Fiscal).

Revision ID: uu11vv913j1s6
Revises: gg66ii792y2
Create Date: 2026-02-27

Campos vindos de estabelecimento_fiscal para unificar em Empresa Fiscal.
"""
import sqlalchemy as sa
from alembic import op

revision = "uu11vv913j1s6"
down_revision = "gg66ii792y2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresa",
        sa.Column("regime_tributario", sa.String(50), nullable=True, comment="Regime tributário (texto, ex: Simples Nacional)"),
    )
    op.add_column(
        "empresa",
        sa.Column("aliquotas_uf", sa.Text(), nullable=True, comment="JSON: alíquotas por UF"),
    )


def downgrade() -> None:
    op.drop_column("empresa", "aliquotas_uf")
    op.drop_column("empresa", "regime_tributario")
