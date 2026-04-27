"""Marketing vitrine: textos padrão reais no singleton (títulos/subtítulos).

Revision ID: mv04_mv_config_textos
Revises: mv03_mv_sec_defaults
Create Date: 2026-03-26
"""
from alembic import op

revision = "mv04_mv_config_textos"
down_revision = "mv03_mv_sec_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE marketing_vitrine_config
        SET
            titulo_ofertas_semana = COALESCE(NULLIF(BTRIM(titulo_ofertas_semana), ''), 'Ofertas da semana'),
            subtitulo_ofertas_semana = COALESCE(
                NULLIF(BTRIM(subtitulo_ofertas_semana), ''),
                'Os melhores descontos para você.'
            ),
            titulo_faixa_destaques = COALESCE(NULLIF(BTRIM(titulo_faixa_destaques), ''), 'Destaques'),
            titulo_em_alta = COALESCE(NULLIF(BTRIM(titulo_em_alta), ''), 'Mais procurados'),
            subtitulo_em_alta = COALESCE(
                NULLIF(BTRIM(subtitulo_em_alta), ''),
                'Produtos que estão chamando atenção.'
            )
        WHERE id = 1
        """
    )


def downgrade() -> None:
    pass
