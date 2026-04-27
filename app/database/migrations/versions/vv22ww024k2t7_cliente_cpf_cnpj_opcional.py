"""Cliente: adicionar CPF e tornar CNPJ opcional (PJ = CNPJ, PF = CPF para destinatário de notas).

Revision ID: vv22ww024k2t7
Revises: merge_empresa_uf
Create Date: 2026-02-27

"""
import sqlalchemy as sa
from alembic import op

revision = "vv22ww024k2t7"
down_revision = "merge_empresa_uf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clientes",
        sa.Column("cpf", sa.String(14), nullable=True),
    )
    op.create_index("ix_clientes_cpf", "clientes", ["cpf"], unique=True)
    op.alter_column(
        "clientes",
        "cnpj",
        existing_type=sa.String(18),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_clientes_cnpj_ou_cpf",
        "clientes",
        "cnpj IS NOT NULL OR cpf IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_clientes_cnpj_ou_cpf", "clientes", type_="check")
    op.alter_column(
        "clientes",
        "cnpj",
        existing_type=sa.String(18),
        nullable=False,
    )
    op.drop_index("ix_clientes_cpf", table_name="clientes")
    op.drop_column("clientes", "cpf")
