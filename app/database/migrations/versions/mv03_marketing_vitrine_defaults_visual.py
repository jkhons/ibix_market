"""Marketing vitrine: defaults de seção = home legada (sem regressão visual).

Revision ID: mv03_mv_sec_defaults (≤32 chars — alembic_version)
Revises: mv02_marketing_vitrine_secoes
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "mv03_mv_sec_defaults"
down_revision = "mv02_marketing_vitrine_secoes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # mv02 usou default false; a home /loja já exibia essas seções — alinhar dados existentes.
    op.execute(
        """
        UPDATE marketing_vitrine_config
        SET mostrar_secao_em_alta = true,
            mostrar_secao_lojas_destaque = true
        """
    )
    op.alter_column(
        "marketing_vitrine_config",
        "mostrar_secao_em_alta",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
    )
    op.alter_column(
        "marketing_vitrine_config",
        "mostrar_secao_lojas_destaque",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
    )


def downgrade() -> None:
    op.alter_column(
        "marketing_vitrine_config",
        "mostrar_secao_em_alta",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
    )
    op.alter_column(
        "marketing_vitrine_config",
        "mostrar_secao_lojas_destaque",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
    )
