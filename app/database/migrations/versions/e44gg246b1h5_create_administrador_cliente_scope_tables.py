"""create administrador_clientes and cliente_administrador_clientes (Saas.md Fase 3)

Revision ID: e44gg246b1h5
Revises: d33ff135a0g4
Create Date: 2026-02-06

"""
import sqlalchemy as sa
from alembic import op

revision = "e44gg246b1h5"
down_revision = "d33ff135a0g4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "administrador_clientes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_administrador_clientes_usuario_id", "administrador_clientes", ["usuario_id"])
    op.create_index("idx_administrador_clientes_cliente_id", "administrador_clientes", ["cliente_id"])

    op.create_table(
        "cliente_administrador_clientes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cliente_admin_clientes_usuario_id", "cliente_administrador_clientes", ["usuario_id"])
    op.create_index("idx_cliente_admin_clientes_cliente_id", "cliente_administrador_clientes", ["cliente_id"])


def downgrade() -> None:
    op.drop_table("cliente_administrador_clientes")
    op.drop_table("administrador_clientes")
