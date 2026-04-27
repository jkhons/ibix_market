"""Notas fiscais: pedido_marketplace_id (NF-e de venda marketplace) e emitido_por_id nullable.

Revision ID: nfe06_mk_nf
Revises: mk02_perm
Create Date: 2026-03-07

- notas_fiscais.pedido_marketplace_id (FK pedidos_marketplace.id) para vincular NF ao pedido da loja.
- notas_fiscais.emitido_por_id passa a nullable (notas criadas por task Celery não têm usuário).
- origem_documento aceita 'venda_marketplace' (string; enum no modelo).
"""
import sqlalchemy as sa
from alembic import op

revision = "nfe06_mk_nf"
down_revision = "mk02_perm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notas_fiscais",
        sa.Column(
            "pedido_marketplace_id",
            sa.Integer(),
            nullable=True,
            comment="ID do pedido da loja (marketplace) quando NF originada de venda na vitrine",
        ),
    )
    op.create_foreign_key(
        "fk_notas_fiscais_pedido_marketplace_id",
        "notas_fiscais",
        "pedidos_marketplace",
        ["pedido_marketplace_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_notas_fiscais_pedido_marketplace",
        "notas_fiscais",
        ["pedido_marketplace_id"],
    )
    op.alter_column(
        "notas_fiscais",
        "emitido_por_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "notas_fiscais",
        "emitido_por_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_index("idx_notas_fiscais_pedido_marketplace", table_name="notas_fiscais")
    op.drop_constraint(
        "fk_notas_fiscais_pedido_marketplace_id",
        "notas_fiscais",
        type_="foreignkey",
    )
    op.drop_column("notas_fiscais", "pedido_marketplace_id")
