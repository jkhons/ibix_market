"""Faixa Destaques: embaralhar ordem dos cards a cada resposta (config global).

Revision ID: mv13_destaque_embaralhar
Revises: mv12_seed_destaque_livre_exemplo
Create Date: 2026-03-27
"""

import sqlalchemy as sa
from alembic import op

revision = "mv13_destaque_embaralhar"
down_revision = "mv12_seed_destaque_livre_exemplo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "marketing_vitrine_config",
        sa.Column(
            "destaque_embaralhar",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        """
        UPDATE marketing_vitrine_config
        SET destaque_embaralhar = false
        WHERE id = 1
        """
    )


def downgrade() -> None:
    op.drop_column("marketing_vitrine_config", "destaque_embaralhar")
