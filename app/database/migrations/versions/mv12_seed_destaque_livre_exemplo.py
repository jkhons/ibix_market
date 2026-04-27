"""Seed opcional: um card «livre» na faixa Destaques (formato completo parametrizável no admin).

Insere apenas se ainda não existir nenhum card tipo_bloco=destaque e tipo_card=livre.

Revision ID: mv12_seed_destaque_livre_exemplo
Revises: mv11_marketing_destaque_params
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op

revision = "mv12_seed_destaque_livre_exemplo"
down_revision = "mv11_marketing_destaque_params"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    n = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM marketing_vitrine_cards "
            "WHERE tipo_bloco = 'destaque' AND tipo_card = 'livre'"
        )
    ).scalar()
    if n and int(n) > 0:
        return
    op.execute(
        sa.text(
            """
            INSERT INTO marketing_vitrine_cards (
                tipo_bloco, tipo_card, titulo, descricao, imagem_url, link_url,
                ordem, ativo, created_at, updated_at
            ) VALUES (
                'destaque',
                'livre',
                'Exemplo — faixa Destaques',
                'Texto editável pelo Superadmin em /admin/marketing-vitrine (card tipo Livre, bloco Destaque).',
                'https://placehold.co/640x360/e8eef5/1a2b3c?text=Destaque',
                '/loja',
                10,
                true,
                NOW(),
                NOW()
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM marketing_vitrine_cards
            WHERE tipo_bloco = 'destaque'
              AND tipo_card = 'livre'
              AND titulo = 'Exemplo — faixa Destaques'
              AND ordem = 10
              AND link_url = '/loja'
              AND imagem_url LIKE 'https://placehold.co/%'
            """
        )
    )
