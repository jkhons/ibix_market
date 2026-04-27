"""Constraint única em movimentacoes_estoque.nfe_item_id para impedir movimentos duplicados por item de NF-e.

Revision ID: nfe02_uk_nfe_item
Revises: nfe01_entrada
Create Date: 2026-03-02

Garante um único movimento de estoque por nfe_item_id (entrada NFe), evitando lançamentos duplicados.
"""
from alembic import op
from sqlalchemy import text

revision = "nfe02_uk_nfe_item"
down_revision = "nfe01_entrada"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Remover duplicatas: manter o registro com menor id por nfe_item_id (evita falha ao criar UNIQUE)
    if conn.dialect.name == "postgresql":
        conn.execute(
            text("""
                DELETE FROM movimentacoes_estoque m
                USING movimentacoes_estoque m2
                WHERE m.nfe_item_id IS NOT NULL
                  AND m.nfe_item_id = m2.nfe_item_id
                  AND m.id > m2.id
            """)
        )
    else:
        conn.execute(
            text("""
                DELETE FROM movimentacoes_estoque
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (PARTITION BY nfe_item_id ORDER BY id) AS rn
                        FROM movimentacoes_estoque
                        WHERE nfe_item_id IS NOT NULL
                    ) sub
                    WHERE rn > 1
                )
            """)
        )

    op.create_unique_constraint(
        "uq_movimentacoes_estoque_nfe_item_id",
        "movimentacoes_estoque",
        ["nfe_item_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_movimentacoes_estoque_nfe_item_id",
        "movimentacoes_estoque",
        type_="unique",
    )
