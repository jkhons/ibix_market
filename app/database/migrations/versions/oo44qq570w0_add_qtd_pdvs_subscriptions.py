"""add qtd_pdvs_contratados to subscriptions (Fase 2 - Etapa 2.3)

Revision ID: oo44qq570w0
Revises: nn33pp469v9
Create Date: 2026-02-20

Etapa 2.3: campo qtd_pdvs_contratados em subscriptions para checagem ao criar PDV.
"""
import sqlalchemy as sa
from alembic import op

revision = "oo44qq570w0"
down_revision = "nn33pp469v9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("qtd_pdvs_contratados", sa.Integer(), nullable=False, server_default=sa.text("1"),
                   comment="Qtd de PDVs contratados nesta subscription"),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "qtd_pdvs_contratados")
