"""Merge Alembic heads: multi-brand (br02) + cm01.

Revision ID: br03_merge_multibrand
Revises: cm01_cliente_material_categorias, br02_brand_modules
Create Date: 2026-06-18
"""
from alembic import op

revision = "br03_merge_multibrand"
down_revision = ("cm01_cliente_material_categorias", "br02_brand_modules")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
