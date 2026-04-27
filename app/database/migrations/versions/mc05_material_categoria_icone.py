"""Adicionar campo icone em material_categoria.

Revision ID: mc05_material_icone
Revises: mc04_lista01
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "mc05_material_icone"
down_revision = "mc04_lista01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("material_categoria", sa.Column("icone", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("material_categoria", "icone")
