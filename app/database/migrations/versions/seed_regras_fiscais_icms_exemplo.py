"""Seed: regras fiscais ICMS de exemplo para motor tributário.

Insere 5 regras por empresa: Simples Nacional (interna/interestadual/qualquer) e Regime Normal (interna/interestadual/qualquer).
A regra "qualquer" cobre notas sem destinatário (tipo_operacao=qualquer).
Só insere se a empresa ainda não tiver nenhuma regra.

Revision ID: seed_regras_icms
Revises: regras_fisc_icms
Create Date: 2026-03-12

"""
import sqlalchemy as sa
from alembic import op

revision = "seed_regras_icms"
down_revision = "regras_fisc_icms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    empresas = conn.execute(
        sa.text("SELECT id, crt FROM empresa WHERE crt IN (1, 2, 3)")
    ).fetchall()

    for (empresa_id, crt) in empresas:
        exists = conn.execute(
            sa.text("SELECT 1 FROM regras_fiscais_icms WHERE empresa_id = :eid LIMIT 1"),
            {"eid": empresa_id},
        ).fetchone()
        if exists:
            continue

        if crt in (1, 2):
            # Simples Nacional - venda interna
            conn.execute(
                sa.text("""
                    INSERT INTO regras_fiscais_icms (
                        empresa_id, ativo, ordem_prioridade, crt, tipo_operacao, tipo_destinatario,
                        cfop, origem_mercadoria, csosn, aliquota_icms, gera_icms_st, created_at, updated_at
                    ) VALUES (
                        :eid, true, 10, :crt, 'venda_interna', 'qualquer',
                        '5102', 0, '102', 0, false, NOW(), NOW()
                    )
                """),
                {"eid": empresa_id, "crt": crt},
            )
            # Simples Nacional - venda interestadual
            conn.execute(
                sa.text("""
                    INSERT INTO regras_fiscais_icms (
                        empresa_id, ativo, ordem_prioridade, crt, tipo_operacao, tipo_destinatario,
                        cfop, origem_mercadoria, csosn, aliquota_icms, gera_icms_st, created_at, updated_at
                    ) VALUES (
                        :eid, true, 20, :crt, 'venda_interestadual', 'qualquer',
                        '6102', 0, '102', 0, false, NOW(), NOW()
                    )
                """),
                {"eid": empresa_id, "crt": crt},
            )
            # Simples Nacional - tipo qualquer (nota sem destinatário)
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
            # Regime Normal - venda interna
            conn.execute(
                sa.text("""
                    INSERT INTO regras_fiscais_icms (
                        empresa_id, ativo, ordem_prioridade, crt, tipo_operacao, tipo_destinatario,
                        cfop, origem_mercadoria, cst_icms, aliquota_icms, gera_icms_st, created_at, updated_at
                    ) VALUES (
                        :eid, true, 10, 3, 'venda_interna', 'qualquer',
                        '5102', 0, '00', 0, false, NOW(), NOW()
                    )
                """),
                {"eid": empresa_id},
            )
            # Regime Normal - venda interestadual
            conn.execute(
                sa.text("""
                    INSERT INTO regras_fiscais_icms (
                        empresa_id, ativo, ordem_prioridade, crt, tipo_operacao, tipo_destinatario,
                        cfop, origem_mercadoria, cst_icms, aliquota_icms, gera_icms_st, created_at, updated_at
                    ) VALUES (
                        :eid, true, 20, 3, 'venda_interestadual', 'qualquer',
                        '6102', 0, '00', 0, false, NOW(), NOW()
                    )
                """),
                {"eid": empresa_id},
            )
            # Regime Normal - tipo qualquer (nota sem destinatário)
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
            WHERE cfop IN ('5102', '6102')
            AND (
                (crt IN (1, 2) AND csosn = '102') OR
                (crt = 3 AND cst_icms = '00')
            )
        """)
    )
