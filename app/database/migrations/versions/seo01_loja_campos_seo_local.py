"""Campos SEO local em lojas_marketplace

Revision ID: seo01_loja_campos_seo
Revises: mp06_frete_item_snapshot
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "seo01_loja_campos_seo"
down_revision = "mp06_frete_item_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lojas_marketplace", sa.Column("categoria_principal", sa.String(length=120), nullable=True))
    op.add_column("lojas_marketplace", sa.Column("subcategoria", sa.String(length=120), nullable=True))
    op.add_column("lojas_marketplace", sa.Column("cidade_seo", sa.String(length=120), nullable=True))
    op.add_column("lojas_marketplace", sa.Column("estado_seo", sa.String(length=2), nullable=True))
    op.add_column("lojas_marketplace", sa.Column("slug_categoria_cidade", sa.String(length=260), nullable=True))
    op.add_column("lojas_marketplace", sa.Column("seo_title", sa.String(length=160), nullable=True))
    op.add_column("lojas_marketplace", sa.Column("seo_description", sa.String(length=320), nullable=True))
    op.add_column("lojas_marketplace", sa.Column("og_image_url", sa.Text(), nullable=True))
    op.add_column(
        "lojas_marketplace",
        sa.Column("seo_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_lojas_marketplace_categoria_principal", "lojas_marketplace", ["categoria_principal"])
    op.create_index("ix_lojas_marketplace_cidade_seo", "lojas_marketplace", ["cidade_seo"])
    op.create_index("ix_lojas_marketplace_slug_categoria_cidade", "lojas_marketplace", ["slug_categoria_cidade"])


def downgrade() -> None:
    op.drop_index("ix_lojas_marketplace_slug_categoria_cidade", table_name="lojas_marketplace")
    op.drop_index("ix_lojas_marketplace_cidade_seo", table_name="lojas_marketplace")
    op.drop_index("ix_lojas_marketplace_categoria_principal", table_name="lojas_marketplace")
    op.drop_column("lojas_marketplace", "seo_enabled")
    op.drop_column("lojas_marketplace", "og_image_url")
    op.drop_column("lojas_marketplace", "seo_description")
    op.drop_column("lojas_marketplace", "seo_title")
    op.drop_column("lojas_marketplace", "slug_categoria_cidade")
    op.drop_column("lojas_marketplace", "estado_seo")
    op.drop_column("lojas_marketplace", "cidade_seo")
    op.drop_column("lojas_marketplace", "subcategoria")
    op.drop_column("lojas_marketplace", "categoria_principal")
