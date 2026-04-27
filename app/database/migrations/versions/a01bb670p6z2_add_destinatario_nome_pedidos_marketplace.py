"""add destinatario_nome to pedidos_marketplace

Revision ID: a01bb670p6z2
Revises: z67bb569o5y1
Create Date: 2026-03-19

Campo opcional para identificar o destinatário real quando diferente do comprador logado.
"""
import sqlalchemy as sa
from alembic import op

revision = "a01bb670p6z2"
down_revision = "ft02_areas_cep"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pedidos_marketplace",
        sa.Column("destinatario_nome", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pedidos_marketplace", "destinatario_nome")
