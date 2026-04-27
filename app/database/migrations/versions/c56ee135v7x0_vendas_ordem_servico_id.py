"""vendas.ordem_servico_id: vínculo 1:1 OS -> Venda para fluxo Enviar para vendas.

Revision ID: c56ee135v7x0
Revises: b99dd680t5v6
Create Date: 2026-02-09

Adiciona ordem_servico_id em vendas (nullable), FK para ordem_servico.id (ondelete SET NULL),
índice ix_vendas_ordem_servico_id e unique uq_vendas_ordem_servico_id para garantir 1:1 no banco.
"""
import sqlalchemy as sa
from alembic import op

revision = "c56ee135v7x0"
down_revision = "b99dd680t5v6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vendas",
        sa.Column(
            "ordem_servico_id",
            sa.Integer(),
            nullable=True,
            comment="ID da ordem de serviço que originou a venda (1:1, Enviar para vendas)",
        ),
    )
    op.create_foreign_key(
        "fk_vendas_ordem_servico_id",
        "vendas",
        "ordem_servico",
        ["ordem_servico_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_vendas_ordem_servico_id", "vendas", ["ordem_servico_id"])
    op.create_unique_constraint("uq_vendas_ordem_servico_id", "vendas", ["ordem_servico_id"])


def downgrade() -> None:
    op.drop_constraint("uq_vendas_ordem_servico_id", "vendas", type_="unique")
    op.drop_index("ix_vendas_ordem_servico_id", table_name="vendas")
    op.drop_constraint("fk_vendas_ordem_servico_id", "vendas", type_="foreignkey")
    op.drop_column("vendas", "ordem_servico_id")
