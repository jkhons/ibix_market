"""Marketing vitrine: parâmetros persistidos da faixa Destaques (layout, setas, snap).

Revision ID: mv11_marketing_destaque_params
Revises: mv10_hero_titulo_1linha
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op

revision = "mv11_marketing_destaque_params"
down_revision = "mv10_hero_titulo_1linha"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "marketing_vitrine_config",
        sa.Column(
            "destaque_layout",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'carrossel'"),
        ),
    )
    op.add_column(
        "marketing_vitrine_config",
        sa.Column(
            "destaque_mostrar_setas",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "marketing_vitrine_config",
        sa.Column(
            "destaque_scroll_snap",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.execute(
        """
        UPDATE marketing_vitrine_config
        SET destaque_layout = 'carrossel',
            destaque_mostrar_setas = true,
            destaque_scroll_snap = true
        WHERE id = 1
        """
    )


def downgrade() -> None:
    op.drop_column("marketing_vitrine_config", "destaque_scroll_snap")
    op.drop_column("marketing_vitrine_config", "destaque_mostrar_setas")
    op.drop_column("marketing_vitrine_config", "destaque_layout")
