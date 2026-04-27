"""Corrige itens de notas fiscais já faturadas: preenche origem, CFOP e CST/CSOSN quando ausentes.

Revision ID: fiscal_corrigir_itens_fat
Revises: fiscal_doc_mapa
Create Date: 2026-03-12

Notas já autorizadas podem ter itens com origem NULL, cfop ou cst/csosn vazios
(emitidas antes das validações atuais). Esta migration preenche valores padrão
para manter consistência e evitar falhas em detalhes/XML sob demanda.
"""
from alembic import op
from sqlalchemy import text

revision = "fiscal_corrigir_itens_fat"
down_revision = "fiscal_doc_mapa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1) Origem da mercadoria: 0 = nacional (padrão seguro quando NULL)
    conn.execute(
        text("""
            UPDATE notas_fiscais_itens
            SET origem = 0
            WHERE origem IS NULL
        """)
    )

    # 2) CFOP: 5102 = venda de mercadoria dentro do estado (padrão comum para NF-e saída)
    conn.execute(
        text("""
            UPDATE notas_fiscais_itens
            SET cfop = '5102'
            WHERE cfop IS NULL OR TRIM(cfop) = ''
        """)
    )

    # 3) Simples Nacional (CRT 1 ou 2): preencher CSOSN quando vazio (102 = tributada sem crédito)
    conn.execute(
        text("""
            UPDATE notas_fiscais_itens i
            SET csosn = '102'
            FROM notas_fiscais n, empresa e
            WHERE i.nota_id = n.id AND n.empresa_id = e.id
              AND e.crt IN (1, 2)
              AND (i.csosn IS NULL OR TRIM(i.csosn) = '')
        """)
    )

    # 4) Regime Normal (CRT 3): preencher CST ICMS quando vazio (00 = tributada integralmente)
    conn.execute(
        text("""
            UPDATE notas_fiscais_itens i
            SET cst_icms = '00'
            FROM notas_fiscais n, empresa e
            WHERE i.nota_id = n.id AND n.empresa_id = e.id
              AND e.crt = 3
              AND (i.cst_icms IS NULL OR TRIM(i.cst_icms) = '')
        """)
    )


def downgrade() -> None:
    # Não revertemos os dados: não há como saber quais linhas foram alteradas
    # nem restaurar NULLs originais. A correção é idempotente e segura.
    pass
