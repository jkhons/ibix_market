"""Adiciona config cupom no tenant (modo impressão e tipo cupom).

Revision ID: cupom_tenant
Revises: nfce_csc_emp
Create Date: 2026-03-16

- cupom_impressao_modo: automatico | manual (default manual)
- cupom_tipo: nao_fiscal | fiscal (default nao_fiscal)
- cupom_fiscal_emissor: interno | externo (futuro, nullable)
"""
import sqlalchemy as sa
from alembic import op

revision = "cupom_tenant"
down_revision = "nfce_csc_emp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "cupom_impressao_modo",
            sa.String(20),
            nullable=True,
            comment="automatico | manual - impressão ao final da venda",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "cupom_tipo",
            sa.String(20),
            nullable=True,
            comment="nao_fiscal | fiscal - tipo de cupom",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "cupom_fiscal_emissor",
            sa.String(20),
            nullable=True,
            comment="interno | externo - futuro, para cupom fiscal",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "cupom_fiscal_emissor")
    op.drop_column("tenants", "cupom_tipo")
    op.drop_column("tenants", "cupom_impressao_modo")
