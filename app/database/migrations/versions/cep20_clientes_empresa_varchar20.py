"""clientes.cep e empresa.cep: garantir VARCHAR(20) (idempotente).

Revision ID: cep20_v20
Revises: merge_nfse_cli
Create Date: 2026-03-02

Evita StringDataRightTruncation para CEPs com formato alternativo (ex.: 18.682-716).
Em PostgreSQL, ALTER para o mesmo tamanho é inócuo.
"""
import sqlalchemy as sa
from alembic import op

revision = "cep20_v20"
down_revision = "merge_nfse_cli"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # clientes.cep: garantir varchar(20) (idempotente se já for 20)
    op.alter_column(
        "clientes",
        "cep",
        existing_type=sa.String(9),
        type_=sa.String(20),
        existing_nullable=True,
    )
    # empresa.cep: varchar(9) -> varchar(20)
    op.alter_column(
        "empresa",
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
    op.alter_column(
        "empresa",
        "cep",
        existing_type=sa.String(20),
        type_=sa.String(9),
        existing_nullable=True,
    )
