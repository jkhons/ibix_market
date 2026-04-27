"""Remover UNIQUE global de clientes.cnpj e clientes.cpf para permitir o mesmo CNPJ/CPF em subclientes de CAs diferentes.

Revision ID: cli02_escopo
Revises: pc06_drop_est
Create Date: 2026-03-03

Permite que um mesmo cliente (CNPJ/CPF) seja cadastrado como subcliente em mais de um CA.
A validação de duplicidade passa a ser por escopo do CA (apenas no módulo/API).
"""
from alembic import op

revision = "cli02_escopo"
down_revision = "pc06_drop_est"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CNPJ: constraint UNIQUE na coluna (nome padrão PostgreSQL: clientes_cnpj_key)
    op.drop_constraint("clientes_cnpj_key", "clientes", type_="unique")
    # CPF: índice único ix_clientes_cpf (criado em vv22ww024k2t7)
    op.drop_index("ix_clientes_cpf", table_name="clientes")
    op.create_index("ix_clientes_cpf", "clientes", ["cpf"], unique=False)


def downgrade() -> None:
    op.create_unique_constraint("clientes_cnpj_key", "clientes", ["cnpj"])
    op.drop_index("ix_clientes_cpf", table_name="clientes")
    op.create_index("ix_clientes_cpf", "clientes", ["cpf"], unique=True)
