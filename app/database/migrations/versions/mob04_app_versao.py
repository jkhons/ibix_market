"""Mobile: tabela app_versao_config com seed inicial.

Revision ID: mob04_app_versao
Revises: mob03_notificacoes
Create Date: 2026-04-13
"""
import sqlalchemy as sa
from alembic import op

revision = "mob04_app_versao"
down_revision = "mob03_notificacoes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_versao_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("plataforma", sa.String(10), nullable=False),
        sa.Column("versao_minima", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("versao_recomendada", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("url_loja", sa.String(500), nullable=True),
        sa.Column("mensagem", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plataforma", name="uq_app_versao_config_plataforma"),
    )

    op.execute(
        "INSERT INTO app_versao_config (plataforma, versao_minima, versao_recomendada, url_loja) VALUES "
        "('ios', '1.0.0', '1.0.0', 'https://apps.apple.com/app/ibix-market/id000000'), "
        "('android', '1.0.0', '1.0.0', 'https://play.google.com/store/apps/details?id=com.ibix.market')"
    )


def downgrade() -> None:
    op.drop_table("app_versao_config")
