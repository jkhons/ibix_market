"""Orçamento: conversão para OS e venda — FKs rastreio; vendas.orcamento_id origem.

Revision ID: or03_orcamento_conversao_os_venda
Revises: pd02_anonymizar_nomes_clientes_vendas_negocio
Create Date: 2026-05-04
"""
import sqlalchemy as sa
from alembic import op

revision = "or03_orcamento_conversao_os_venda"
down_revision = "pd02_anonymizar_nomes_clientes_vendas_negocio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vendas", sa.Column("orcamento_id", sa.Integer(), nullable=True))
    op.create_index("ix_vendas_orcamento_id", "vendas", ["orcamento_id"])

    op.add_column("orcamentos", sa.Column("convertido_em_ordem_servico_id", sa.Integer(), nullable=True))
    op.add_column("orcamentos", sa.Column("convertido_em_venda_id", sa.Integer(), nullable=True))
    op.create_index(
        "ix_orcamentos_convertido_em_ordem_servico_id",
        "orcamentos",
        ["convertido_em_ordem_servico_id"],
    )
    op.create_index(
        "ix_orcamentos_convertido_em_venda_id",
        "orcamentos",
        ["convertido_em_venda_id"],
    )

    op.create_foreign_key(
        "fk_orcamentos_convertido_em_ordem_servico_id",
        "orcamentos",
        "ordem_servico",
        ["convertido_em_ordem_servico_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_orcamentos_convertido_em_venda_id",
        "orcamentos",
        "vendas",
        ["convertido_em_venda_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_vendas_orcamento_id",
        "vendas",
        "orcamentos",
        ["orcamento_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_vendas_orcamento_id", "vendas", type_="foreignkey")
    op.drop_constraint("fk_orcamentos_convertido_em_venda_id", "orcamentos", type_="foreignkey")
    op.drop_constraint("fk_orcamentos_convertido_em_ordem_servico_id", "orcamentos", type_="foreignkey")

    op.drop_index("ix_orcamentos_convertido_em_venda_id", table_name="orcamentos")
    op.drop_index("ix_orcamentos_convertido_em_ordem_servico_id", table_name="orcamentos")
    op.drop_column("orcamentos", "convertido_em_venda_id")
    op.drop_column("orcamentos", "convertido_em_ordem_servico_id")

    op.drop_index("ix_vendas_orcamento_id", table_name="vendas")
    op.drop_column("vendas", "orcamento_id")
