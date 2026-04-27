"""Mobile: tabela consumidor_favoritos.

Revision ID: mob02_favoritos
Revises: mob01_push_refresh
Create Date: 2026-04-13
"""
import sqlalchemy as sa
from alembic import op

revision = "mob02_favoritos"
down_revision = "mob01_push_refresh"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consumidor_favoritos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("consumidor_id", sa.Integer(), nullable=False),
        sa.Column("anuncio_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["consumidor_id"], ["consumidores_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["anuncio_id"], ["anuncios_plataforma.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("consumidor_id", "anuncio_id", name="uq_consumidor_favoritos_consumidor_anuncio"),
    )
    op.create_index("ix_consumidor_favoritos_consumidor_id", "consumidor_favoritos", ["consumidor_id"])
    op.create_index("ix_consumidor_favoritos_anuncio_id", "consumidor_favoritos", ["anuncio_id"])


def downgrade() -> None:
    op.drop_index("ix_consumidor_favoritos_anuncio_id", table_name="consumidor_favoritos")
    op.drop_index("ix_consumidor_favoritos_consumidor_id", table_name="consumidor_favoritos")
    op.drop_table("consumidor_favoritos")
