"""empresa: gateway_plataforma (SuperAdmin escolhe provedor no modo plataforma).

Revision ID: em02_gateway_plataforma
Revises: merge_mc04_rs01
Create Date: 2026-03-24

"""
import sqlalchemy as sa
from alembic import op

revision = "em02_gateway_plataforma"
down_revision = "merge_mc04_rs01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresa",
        sa.Column(
            "gateway_plataforma",
            sa.String(length=30),
            nullable=False,
            server_default="mercadopago",
            comment="mercadopago|pagbank|pagarme — gateway usado quando modo_recebimento=plataforma",
        ),
    )


def downgrade() -> None:
    op.drop_column("empresa", "gateway_plataforma")
