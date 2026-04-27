"""Drop tabelas afericoes_programadas, comprovantes_afericao, contratos_afericao

Revision ID: hh77jj803z3
Revises: gg66ii792y2
Create Date: 2026-02-18

Remove tabelas do módulo de aferições e contratos de aferição.
Ordem: filhos antes de pais; remove FK de agendamentos antes de dropar contratos_afericao.
"""
from alembic import op
from sqlalchemy import text

revision = "hh77jj803z3"
down_revision = "gg66ii792y2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # 1. Drop comprovantes_afericao (FK para afericoes_programadas)
    conn.execute(text("DROP TABLE IF EXISTS comprovantes_afericao CASCADE"))
    # 2. Drop afericoes_programadas (FK para contratos_afericao, equipamentos)
    conn.execute(text("DROP TABLE IF EXISTS afericoes_programadas CASCADE"))
    # 3. Remover FK de agendamentos para contratos_afericao
    conn.execute(text("ALTER TABLE agendamentos DROP COLUMN IF EXISTS contrato_afericao_id"))
    # 4. Drop contratos_afericao
    conn.execute(text("DROP TABLE IF EXISTS contratos_afericao CASCADE"))


def downgrade() -> None:
    # Não recriamos as tabelas — módulo foi removido.
    pass
