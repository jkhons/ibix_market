"""clientes.cep: varchar(9) -> varchar(20)

Revision ID: cli01_cep20
Revises: usu01_usr_cpf
Create Date: 2026-03-02

Evita StringDataRightTruncation quando CEP vem com formato alternativo (ex.: 18.682-716).
"""
import sqlalchemy as sa
from alembic import op

revision = "cli01_cep20"
down_revision = "usu01_usr_cpf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "clientes",
        "cep",
        existing_type=sa.String(9),
        type_=sa.String(20),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "clientes",
        "cep",
        existing_type=sa.String(20),
        type_=sa.String(9),
        existing_nullable=True,
    )
