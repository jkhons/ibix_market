"""Adiciona cfop_padrao e referencia em produtos_cliente (modal Editar Produto - negócios/estoque).

Revision ID: pc01_cfop_ref
Revises: nfe02_uk_nfe_item
Create Date: 2026-03-03

"""
import sqlalchemy as sa
from alembic import op

revision = "pc01_cfop_ref"
down_revision = "nfe02_uk_nfe_item"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("produtos_cliente", sa.Column("cfop_padrao", sa.String(10), nullable=True))
    op.add_column("produtos_cliente", sa.Column("referencia", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("produtos_cliente", "referencia")
    op.drop_column("produtos_cliente", "cfop_padrao")
