"""Categorias da vitrine selecionadas pelo lojista (CA) no cadastro público.

Revision ID: cm01_cliente_material_categorias
Revises: tr02_plataforma_cidades
Create Date: 2026-05-21
"""
import sqlalchemy as sa
from alembic import op

revision = "cm01_cliente_material_categorias"
down_revision = "tr02_plataforma_cidades"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cliente_material_categorias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("material_categoria_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_categoria_id"], ["material_categoria.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cliente_id",
            "material_categoria_id",
            name="uq_cliente_material_categoria",
        ),
    )
    op.create_index(
        "ix_cliente_material_categorias_cliente_id",
        "cliente_material_categorias",
        ["cliente_id"],
    )
    op.create_index(
        "ix_cliente_material_categorias_material_categoria_id",
        "cliente_material_categorias",
        ["material_categoria_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cliente_material_categorias_material_categoria_id", table_name="cliente_material_categorias")
    op.drop_index("ix_cliente_material_categorias_cliente_id", table_name="cliente_material_categorias")
    op.drop_table("cliente_material_categorias")
