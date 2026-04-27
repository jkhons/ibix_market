"""anuncios_plataforma: URL opcional de imagem OG (1.91:1 / Fase 02 Meta).

Revision ID: mv15_anuncio_og_image_url
Revises: fc02_forn_tel_nfe_xml
Create Date: 2026-04-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "mv15_anuncio_og_image_url"
down_revision = "fc02_forn_tel_nfe_xml"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "anuncios_plataforma",
        sa.Column("og_image_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("anuncios_plataforma", "og_image_url")
