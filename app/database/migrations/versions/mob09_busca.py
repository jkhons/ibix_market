"""Mobile: tabela termos_buscados (autocomplete + populares).

Revision ID: mob09_busca
Revises: mob08_lgpd
Create Date: 2026-04-13
"""
import sqlalchemy as sa
from alembic import op

revision = "mob09_busca"
down_revision = "mob08_lgpd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "termos_buscados",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("termo", sa.String(255), nullable=False),
        sa.Column("contagem", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("termo", name="uq_termos_buscados_termo"),
    )
    op.create_index("ix_termos_buscados_contagem", "termos_buscados", ["contagem"])


def downgrade() -> None:
    op.drop_index("ix_termos_buscados_contagem", table_name="termos_buscados")
    op.drop_table("termos_buscados")
