"""Drop tabelas calibração/certificados

Revision ID: aa00cc247s6
Revises: a78dd581k6l3
Create Date: 2026-02-17

Remove 19 tabelas obsoletas do módulo de calibração/certificados.
Ordem: filhos antes de pais, CASCADE para certificados e processos.
"""
from alembic import op
from sqlalchemy import text

revision = "aa00cc247s6"
down_revision = "a78dd581k6l3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # 1. Filhos de certificados
    conn.execute(text("DROP TABLE IF EXISTS historico_afericoes CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS renovacoes_certificados CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS condicoes_ambientais CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS pesos_padrao CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS ensaios_excentricidade CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS resultados_ensaios CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS ensaios_mobilidade CASCADE"))

    # 2. Snapshots de certificado
    conn.execute(text("DROP TABLE IF EXISTS certificado_peso_snapshot CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS certificado_equipamento_auxiliar_snapshot CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS certificado_snapshot CASCADE"))

    # 3. Certificados (CASCADE remove FKs de ordem_servico, agendamentos, reclamacoes, etc.)
    conn.execute(text("DROP TABLE IF EXISTS certificados CASCADE"))

    # 4. Filhos de processo_balanca_calibracao
    conn.execute(text("DROP TABLE IF EXISTS processo_balanca_certificados_peso CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS processo_balanca_equipamentos_auxiliares CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS processo_balanca_aux_cadastros CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS processo_balanca_inspetores CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS processo_balanca_aprovadores CASCADE"))

    # 5. processo_balanca_calibracao
    conn.execute(text("DROP TABLE IF EXISTS processo_balanca_calibracao CASCADE"))

    # 6. processo_equipamentos
    conn.execute(text("DROP TABLE IF EXISTS processo_equipamentos CASCADE"))

    # 7. processos (CASCADE remove FKs de ordem_servico, reclamacoes, estoque, etc.)
    conn.execute(text("DROP TABLE IF EXISTS processos CASCADE"))

    # 8. agendamento_equipamentos
    conn.execute(text("DROP TABLE IF EXISTS agendamento_equipamentos CASCADE"))

    # 9. Remover colunas FK órfãs (tabelas que permanecem)
    conn.execute(text("ALTER TABLE agendamentos DROP COLUMN IF EXISTS certificado_id"))
    conn.execute(text("ALTER TABLE reclamacoes DROP COLUMN IF EXISTS certificado_id"))
    conn.execute(text("ALTER TABLE reclamacoes DROP COLUMN IF EXISTS processo_id"))
    conn.execute(text("ALTER TABLE ordem_servico DROP COLUMN IF EXISTS processo_relacionado_id"))
    conn.execute(text("ALTER TABLE assinaturas DROP COLUMN IF EXISTS certificado_id"))
    conn.execute(text("ALTER TABLE notas_certificados DROP COLUMN IF EXISTS certificado_id"))
    conn.execute(text("ALTER TABLE afericoes_programadas DROP COLUMN IF EXISTS certificado_id"))
    conn.execute(text("ALTER TABLE historico_selo_inmetro_reparo DROP COLUMN IF EXISTS processo_id"))
    conn.execute(text("ALTER TABLE estoque DROP COLUMN IF EXISTS processo_id"))
    conn.execute(text("ALTER TABLE acoes_corretivas DROP COLUMN IF EXISTS processo_id"))


def downgrade() -> None:
    # Não recriamos as tabelas — módulo foi removido.
    pass
