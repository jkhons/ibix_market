"""add empresa.cliente_id (vinculo empresa fiscal ao cliente direto - Cliente Administrador)

Revision ID: n33pp135h0q4
Revises: m22oo024i9p3
Create Date: 2026-02-08

Empresa fiscal passa a pertencer obrigatoriamente a um cliente (cliente direto do sistema).
"""
import sqlalchemy as sa
from alembic import op

revision = "n33pp135h0q4"
down_revision = "m22oo024i9p3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresa",
        sa.Column("cliente_id", sa.Integer(), nullable=True, comment="Cliente (cliente direto) a que a empresa fiscal pertence"),
    )
    op.create_foreign_key(
        "fk_empresa_cliente_id",
        "empresa",
        "clientes",
        ["cliente_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_empresa_cliente_id", "empresa", ["cliente_id"])


def downgrade() -> None:
    op.drop_index("idx_empresa_cliente_id", table_name="empresa")
    op.drop_constraint("fk_empresa_cliente_id", "empresa", type_="foreignkey")
    op.drop_column("empresa", "cliente_id")
