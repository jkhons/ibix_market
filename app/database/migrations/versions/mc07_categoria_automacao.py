"""Criar categoria de estoque Automação com ícone.

Revision ID: mc07_categoria_automacao
Revises: mc06_seed_material_icones
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "mc07_categoria_automacao"
down_revision = "mc06_seed_material_icones"
branch_labels = None
depends_on = None


CATEGORIA_CODIGO = "AUTOMACAO"
CATEGORIA_NOME = "Automação"
CATEGORIA_ICONE = "/static/icones/categorias/automacao.svg"


def upgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(
        sa.text("SELECT id FROM material_categoria WHERE codigo = :codigo"),
        {"codigo": CATEGORIA_CODIGO},
    ).fetchone()
    if row:
        conn.execute(
            sa.text(
                """
                UPDATE material_categoria
                SET nome = :nome,
                    icone = :icone,
                    ativo = true
                WHERE codigo = :codigo
                """
            ),
            {
                "nome": CATEGORIA_NOME,
                "icone": CATEGORIA_ICONE,
                "codigo": CATEGORIA_CODIGO,
            },
        )
        return

    conn.execute(
        sa.text(
            """
            INSERT INTO material_categoria (
                nome, descricao, codigo, icone, ativo,
                controla_estoque, permite_negativo, tem_validade,
                dias_alerta_vencimento, requer_aprovacao, limite_movimentacao,
                incluir_relatorios, cor_relatorio
            ) VALUES (
                :nome, :descricao, :codigo, :icone, true,
                true, false, false,
                30, false, NULL,
                true, '#007bff'
            )
            """
        ),
        {
            "nome": CATEGORIA_NOME,
            "descricao": "Produtos e soluções de automação",
            "codigo": CATEGORIA_CODIGO,
            "icone": CATEGORIA_ICONE,
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM material_categoria WHERE codigo = :codigo"),
        {"codigo": CATEGORIA_CODIGO},
    )
