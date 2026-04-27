"""Drop tabelas aux_cadastros, qualidade, lacres, historico_selos e legados

Revision ID: ii88kk914a4
Revises: hh77jj803z3
Create Date: 2026-02-18

Remove FKs de ordem_servico/ordem_servico_itens; drop tabelas de aux cadastros,
qualidade (reclamacoes, procedimentos_metodo, treinamentos_competencia, auditorias_internas),
lacres/selos e historico, e tabelas legadas (certificados_auxiliares, certificados_pesos,
inspetores_aprovadores). Não afeta PDV (vendas, caixa, estoque).
"""
from alembic import op
from sqlalchemy import text

revision = "ii88kk914a4"
down_revision = "hh77jj803z3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Remover FKs/colunas em tabelas que permanecem (ordem_servico, ordem_servico_itens)
    conn.execute(text("ALTER TABLE ordem_servico DROP COLUMN IF EXISTS lacre_utilizado_id"))
    conn.execute(text("ALTER TABLE ordem_servico_itens DROP COLUMN IF EXISTS lacre_lote_id"))
    conn.execute(text("ALTER TABLE ordem_servico_itens DROP COLUMN IF EXISTS historico_selo_id"))
    conn.execute(text("ALTER TABLE ordem_servico_itens DROP COLUMN IF EXISTS lacre_serial"))

    # 2. Drop tabelas que referenciam lacres_selos ou aux_cadastros (filhos primeiro)
    conn.execute(text("DROP TABLE IF EXISTS historico_selo_inmetro_reparo CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS ensaio_pesos_utilizados CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS treinamentos_competencia CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS processo_balanca_aux_cadastros CASCADE"))

    # 3. Drop aux_cadastros (aux_arquivos antes de aux_cadastros)
    conn.execute(text("DROP TABLE IF EXISTS aux_arquivos CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS aux_cadastros CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS aux_categorias CASCADE"))

    # 4. Drop qualidade e lacres
    conn.execute(text("DROP TABLE IF EXISTS reclamacoes CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS procedimentos_metodo CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS lacres_selos CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS auditorias_internas CASCADE"))

    # 5. Drop tabelas legadas (se existirem)
    conn.execute(text("DROP TABLE IF EXISTS certificados_auxiliares CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS certificados_pesos CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS inspetores_aprovadores CASCADE"))


def downgrade() -> None:
    # Não recriamos as tabelas — módulos foram removidos.
    pass
