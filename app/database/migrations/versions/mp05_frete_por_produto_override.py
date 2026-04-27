"""Frete por produto no anuncio marketplace

Revision ID: mp05_frete_produto
Revises: mc06_seed_material_icones
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "mp05_frete_produto"
down_revision = "mc06_seed_material_icones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "anuncios_plataforma",
        sa.Column("frete_sobrescrever_loja", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "anuncios_plataforma",
        sa.Column("formato_frete_produto", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "anuncios_plataforma",
        sa.Column("taxa_entrega_fixa_produto", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "anuncios_plataforma",
        sa.Column("entrega_gratis_apos_produto", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("anuncios_plataforma", "entrega_gratis_apos_produto")
    op.drop_column("anuncios_plataforma", "taxa_entrega_fixa_produto")
    op.drop_column("anuncios_plataforma", "formato_frete_produto")
    op.drop_column("anuncios_plataforma", "frete_sobrescrever_loja")
