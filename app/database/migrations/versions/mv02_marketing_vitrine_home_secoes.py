"""Marketing vitrine: flags de seções da home e títulos parametrizados.

Revision ID: mv02_marketing_vitrine_secoes
Revises: merge_gc01_mc07_mv01
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "mv02_marketing_vitrine_secoes"
down_revision = "merge_gc01_mc07_mv01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "marketing_vitrine_config",
        sa.Column("mostrar_hero_carrossel", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "marketing_vitrine_config",
        sa.Column("mostrar_secao_em_alta", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "marketing_vitrine_config",
        sa.Column("mostrar_secao_lojas_destaque", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "marketing_vitrine_config",
        sa.Column("titulo_faixa_destaques", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "marketing_vitrine_config",
        sa.Column("titulo_em_alta", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "marketing_vitrine_config",
        sa.Column("subtitulo_em_alta", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("marketing_vitrine_config", "subtitulo_em_alta")
    op.drop_column("marketing_vitrine_config", "titulo_em_alta")
    op.drop_column("marketing_vitrine_config", "titulo_faixa_destaques")
    op.drop_column("marketing_vitrine_config", "mostrar_secao_lojas_destaque")
    op.drop_column("marketing_vitrine_config", "mostrar_secao_em_alta")
    op.drop_column("marketing_vitrine_config", "mostrar_hero_carrossel")
