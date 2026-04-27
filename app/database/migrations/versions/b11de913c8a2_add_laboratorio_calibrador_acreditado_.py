"""add laboratorio_calibrador acreditado_por rastreabilidade ISO17025

Revision ID: b11de913c8a2
Revises:
Create Date: 2026-02-06

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'b11de913c8a2'
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(conn, name):
    r = conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :t"
    ), {"t": name})
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    # aux_cadastros: rastreabilidade metrológica (ISO 17025 6.5) — tabela pode ter sido dropada (ii88kk914a4)
    if _table_exists(conn, 'aux_cadastros'):
        op.add_column('aux_cadastros', sa.Column('laboratorio_calibrador', sa.String(255), nullable=True))
        op.add_column('aux_cadastros', sa.Column('acreditado_por', sa.String(100), nullable=True))

    # certificado_peso_snapshot: copiar para snapshot
    if _table_exists(conn, 'certificado_peso_snapshot'):
        op.add_column('certificado_peso_snapshot', sa.Column('laboratorio_calibrador', sa.String(255), nullable=True))
        op.add_column('certificado_peso_snapshot', sa.Column('acreditado_por', sa.String(100), nullable=True))

    # certificado_equipamento_auxiliar_snapshot: copiar para snapshot
    if _table_exists(conn, 'certificado_equipamento_auxiliar_snapshot'):
        op.add_column('certificado_equipamento_auxiliar_snapshot', sa.Column('laboratorio_calibrador', sa.String(255), nullable=True))
        op.add_column('certificado_equipamento_auxiliar_snapshot', sa.Column('acreditado_por', sa.String(100), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, 'certificado_equipamento_auxiliar_snapshot'):
        op.drop_column('certificado_equipamento_auxiliar_snapshot', 'acreditado_por')
        op.drop_column('certificado_equipamento_auxiliar_snapshot', 'laboratorio_calibrador')
    if _table_exists(conn, 'certificado_peso_snapshot'):
        op.drop_column('certificado_peso_snapshot', 'acreditado_por')
        op.drop_column('certificado_peso_snapshot', 'laboratorio_calibrador')
    if _table_exists(conn, 'aux_cadastros'):
        op.drop_column('aux_cadastros', 'acreditado_por')
        op.drop_column('aux_cadastros', 'laboratorio_calibrador')
