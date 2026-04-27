"""Seed: regras fiscais ICMS tipo 'qualquer' para notas sem destinatário.

Adiciona regra tipo_operacao='qualquer' em empresas que têm regras mas não têm essa.
Cobre emissão de NF-e sem cliente (tipo_operacao=qualquer no contexto).

Revision ID: seed_regras_qualquer
Revises: seed_regras_icms
Create Date: 2026-03-12

"""
import sqlalchemy as sa
from alembic import op

revision = "seed_regras_qualquer"
down_revision = "seed_regras_icms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Empresas que têm regras mas não têm tipo_operacao='qualquer'
    empresas_sem_qualquer = conn.execute(
        sa.text("""
            SELECT DISTINCT r.empresa_id, e.crt
            FROM regras_fiscais_icms r
            JOIN empresa e ON e.id = r.empresa_id
            WHERE e.crt IN (1, 2, 3)
            AND r.empresa_id NOT IN (
                SELECT empresa_id FROM regras_fiscais_icms
                WHERE tipo_operacao = 'qualquer' AND ativo = true
            )
        """)
    ).fetchall()

    for (empresa_id, crt) in empresas_sem_qualquer:
        if crt in (1, 2):
            conn.execute(
                sa.text("""
                    INSERT INTO regras_fiscais_icms (
                        empresa_id, ativo, ordem_prioridade, crt, tipo_operacao, tipo_destinatario,
                        cfop, origem_mercadoria, csosn, aliquota_icms, gera_icms_st, created_at, updated_at
                    ) VALUES (
                        :eid, true, 5, :crt, 'qualquer', 'qualquer',
                        '5102', 0, '102', 0, false, NOW(), NOW()
                    )
                """),
                {"eid": empresa_id, "crt": crt},
            )
        else:
            conn.execute(
                sa.text("""
                    INSERT INTO regras_fiscais_icms (
                        empresa_id, ativo, ordem_prioridade, crt, tipo_operacao, tipo_destinatario,
                        cfop, origem_mercadoria, cst_icms, aliquota_icms, gera_icms_st, created_at, updated_at
                    ) VALUES (
                        :eid, true, 5, 3, 'qualquer', 'qualquer',
                        '5102', 0, '00', 0, false, NOW(), NOW()
                    )
                """),
                {"eid": empresa_id},
            )


def downgrade() -> None:
    op.execute(
        sa.text("""
            DELETE FROM regras_fiscais_icms
            WHERE tipo_operacao = 'qualquer'
            AND cfop = '5102'
            AND (
                (crt IN (1, 2) AND csosn = '102') OR
                (crt = 3 AND cst_icms = '00')
            )
        """)
    )
