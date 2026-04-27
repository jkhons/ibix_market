"""Loja marketplace: nome_fantasia, descricao_curta, descricao_longa

Revision ID: seo03_nf_desc (<=32 chars para alembic_version)
Revises: seo02_loja_slug_history
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "seo03_nf_desc"
down_revision = "seo02_loja_slug_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lojas_marketplace", sa.Column("nome_fantasia", sa.String(length=200), nullable=True))
    op.add_column("lojas_marketplace", sa.Column("descricao_curta", sa.String(length=320), nullable=True))
    op.add_column("lojas_marketplace", sa.Column("descricao_longa", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE lojas_marketplace
        SET nome_fantasia = nome_loja
        WHERE nome_fantasia IS NULL AND nome_loja IS NOT NULL AND trim(nome_loja) <> ''
        """
    )
    op.execute(
        """
        UPDATE lojas_marketplace
        SET descricao_longa = descricao
        WHERE descricao_longa IS NULL AND descricao IS NOT NULL AND trim(descricao) <> ''
        """
    )


def downgrade() -> None:
    op.drop_column("lojas_marketplace", "descricao_longa")
    op.drop_column("lojas_marketplace", "descricao_curta")
    op.drop_column("lojas_marketplace", "nome_fantasia")
