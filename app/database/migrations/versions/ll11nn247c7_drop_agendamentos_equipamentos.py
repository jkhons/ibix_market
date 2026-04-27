"""Drop tabelas agendamentos e equipamentos

Revision ID: ll11nn247c7
Revises: kk00mm136b6
Create Date: 2026-02-20

Remove módulos Agendamentos e Equipamentos do banco de dados.
Ordem: remover FKs dependentes, depois dropar tabelas.
"""
from alembic import op
from sqlalchemy import text

revision = "ll11nn247c7"
down_revision = "kk00mm136b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Tabela junction ordem_servico_equipamentos (FK para equipamentos e ordem_servico)
    conn.execute(text("DROP TABLE IF EXISTS ordem_servico_equipamentos CASCADE"))

    # 2. Remover colunas que referenciam agendamentos e equipamentos
    # ordem_servico.agendamento_id
    conn.execute(text("ALTER TABLE ordem_servico DROP COLUMN IF EXISTS agendamento_id"))
    # estoque.agendamento_id e estoque.equipamento_id
    conn.execute(text("ALTER TABLE estoque DROP COLUMN IF EXISTS agendamento_id"))
    conn.execute(text("ALTER TABLE estoque DROP COLUMN IF EXISTS equipamento_id"))

    # 3. Drop agendamentos
    conn.execute(text("DROP TABLE IF EXISTS agendamentos CASCADE"))

    # 4. Drop equipamentos
    conn.execute(text("DROP TABLE IF EXISTS equipamentos CASCADE"))


def downgrade() -> None:
    # Não recriamos as tabelas — módulos foram removidos.
    pass
