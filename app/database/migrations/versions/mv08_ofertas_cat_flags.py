"""Marketing vitrine: cabecalho — categoria_ids (JSONB), embaralhar, somente_com_desconto.

Revision ID: mv08_ofertas_cat_flags
Revises: mv07_cabecalho_ofertas
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "mv08_ofertas_cat_flags"
down_revision = "mv07_cabecalho_ofertas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "marketing_vitrine_cards",
        sa.Column("categoria_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "marketing_vitrine_cards",
        sa.Column("embaralhar_produtos", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "marketing_vitrine_cards",
        sa.Column("somente_com_desconto", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("marketing_vitrine_cards", "somente_com_desconto")
    op.drop_column("marketing_vitrine_cards", "embaralhar_produtos")
    op.drop_column("marketing_vitrine_cards", "categoria_ids")
