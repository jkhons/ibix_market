"""Marketing vitrine: permite múltiplos anúncios em um único card.

Revision ID: mv14_marketing_card_anuncio_ids
Revises: mv13_destaque_embaralhar
Create Date: 2026-03-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "mv14_marketing_card_anuncio_ids"
down_revision = "mv13_destaque_embaralhar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "marketing_vitrine_cards",
        sa.Column("anuncio_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute(
        """
        UPDATE marketing_vitrine_cards
           SET anuncio_ids = jsonb_build_array(anuncio_id)
         WHERE tipo_card = 'anuncio'
           AND anuncio_id IS NOT NULL
           AND anuncio_ids IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("marketing_vitrine_cards", "anuncio_ids")

