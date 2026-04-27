"""Marketing vitrine: card cabecalho_ofertas + coluna limite_exibicao; migra texto do singleton.

Revision ID: mv07_cabecalho_ofertas
Revises: mv06_mv_config_limite_ofertas
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "mv07_cabecalho_ofertas"
down_revision = "mv06_mv_config_limite_ofertas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "marketing_vitrine_cards",
        sa.Column("limite_exibicao", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        INSERT INTO marketing_vitrine_cards (
            tipo_bloco, tipo_card, titulo, descricao, ordem, ativo,
            limite_exibicao, imagem_url, link_url, anuncio_id,
            created_at, updated_at
        )
        SELECT
            'oferta_semana',
            'cabecalho_ofertas',
            NULLIF(BTRIM(titulo_ofertas_semana), ''),
            NULLIF(BTRIM(COALESCE(subtitulo_ofertas_semana, '')), ''),
            0,
            true,
            COALESCE(limite_ofertas_semana, 8),
            NULL,
            NULL,
            NULL,
            now(),
            now()
        FROM marketing_vitrine_config
        WHERE id = 1
          AND NOT EXISTS (
              SELECT 1 FROM marketing_vitrine_cards c
              WHERE c.tipo_bloco = 'oferta_semana' AND c.tipo_card = 'cabecalho_ofertas'
          )
        """
    )
    op.execute(
        """
        UPDATE marketing_vitrine_config
        SET
            titulo_ofertas_semana = NULL,
            subtitulo_ofertas_semana = NULL,
            limite_ofertas_semana = 8
        WHERE id = 1
        """
    )


def downgrade() -> None:
    op.drop_column("marketing_vitrine_cards", "limite_exibicao")
