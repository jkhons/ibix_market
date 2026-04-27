"""Tabelas material_categoria (se não existir), tipo_material e coluna tipo_material_id em produtos_cliente.

Revision ID: mc01_tables
Revises: pc07_foto_midias
Create Date: 2026-03-08

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "mc01_tables"
down_revision = "pc07_foto_midias"
branch_labels = None
depends_on = None


def _material_categoria_columns():
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("controla_estoque", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("permite_negativo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tem_validade", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dias_alerta_vencimento", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("requer_aprovacao", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("limite_movimentacao", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("incluir_relatorios", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cor_relatorio", sa.String(7), nullable=False, server_default=sa.text("'#007bff'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    conn = op.get_bind()
    insp = inspect(conn)
    if not insp.has_table("material_categoria"):
        op.create_table(
            "material_categoria",
            *_material_categoria_columns(),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_material_categoria_codigo", "material_categoria", ["codigo"], unique=True)
        op.create_index("ix_material_categoria_nome", "material_categoria", ["nome"], unique=True)

    op.create_table(
        "tipo_material",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tipo_material_codigo", "tipo_material", ["codigo"], unique=True)

    op.add_column(
        "produtos_cliente",
        sa.Column("tipo_material_id", sa.Integer(), sa.ForeignKey("tipo_material.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_produtos_cliente_tipo_material_id", "produtos_cliente", ["tipo_material_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_produtos_cliente_tipo_material_id", table_name="produtos_cliente")
    op.drop_column("produtos_cliente", "tipo_material_id")
    op.drop_index("ix_tipo_material_codigo", table_name="tipo_material")
    op.drop_table("tipo_material")
    # material_categoria não é removida no downgrade (pode ter sido criada antes ou por outro meio)
