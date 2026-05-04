"""Marketplace: regras de taxa (billing) + custos estimados em anuncios_plataforma.

Revision ID: mt01_marketplace_taxa_regras
Revises: aa78cc680p7z3
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "mt01_marketplace_taxa_regras"
down_revision = "aa78cc680p7z3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_taxa_regras",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("escopo", sa.String(length=20), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.CheckConstraint("escopo IN ('geral', 'tenant')", name="ck_marketplace_taxa_regras_escopo"),
        sa.CheckConstraint(
            "(escopo = 'geral' AND tenant_id IS NULL) OR (escopo = 'tenant' AND tenant_id IS NOT NULL)",
            name="ck_marketplace_taxa_regras_escopo_tenant",
        ),
    )
    op.create_index("ix_marketplace_taxa_regras_tenant_id", "marketplace_taxa_regras", ["tenant_id"])
    op.create_index("ix_marketplace_taxa_regras_escopo_ativo", "marketplace_taxa_regras", ["escopo", "ativo"])

    op.add_column(
        "anuncios_plataforma",
        sa.Column("custo_plataforma_estimado", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "anuncios_plataforma",
        sa.Column("custo_cartao_estimado", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("anuncios_plataforma", "custo_cartao_estimado")
    op.drop_column("anuncios_plataforma", "custo_plataforma_estimado")
    op.drop_index("ix_marketplace_taxa_regras_escopo_ativo", table_name="marketplace_taxa_regras")
    op.drop_index("ix_marketplace_taxa_regras_tenant_id", table_name="marketplace_taxa_regras")
    op.drop_table("marketplace_taxa_regras")
