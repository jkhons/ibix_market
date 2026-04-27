"""Marketing vitrine: limite configurável para "Ofertas da semana".

Revision ID: mv06_mv_config_limite_ofertas
Revises: mv05_mv_textos_admin
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op

revision = "mv06_mv_config_limite_ofertas"
down_revision = "mv05_mv_textos_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "marketing_vitrine_config",
        sa.Column("limite_ofertas_semana", sa.Integer(), nullable=False, server_default="8"),
    )
    # Garante valor para o singleton já existente (id=1).
    op.execute("UPDATE marketing_vitrine_config SET limite_ofertas_semana = 8 WHERE id = 1")


def downgrade() -> None:
    op.drop_column("marketing_vitrine_config", "limite_ofertas_semana")

