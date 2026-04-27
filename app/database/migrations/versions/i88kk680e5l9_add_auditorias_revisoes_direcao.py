"""add auditorias_internas revisoes_direcao ISO17025 5.12 5.13

Revision ID: i88kk680e5l9
Revises: h77jj579d4k8
Create Date: 2026-02-06

"""
import sqlalchemy as sa
from alembic import op

revision = 'i88kk680e5l9'
down_revision = 'h77jj579d4k8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'auditorias_internas',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('numero', sa.String(50), nullable=False),
        sa.Column('escopo', sa.Text(), nullable=False),
        sa.Column('data_planejada', sa.Date(), nullable=False),
        sa.Column('data_realizada', sa.Date(), nullable=True),
        sa.Column('auditores', sa.Text(), nullable=True),
        sa.Column('resultado', sa.String(50), nullable=True),
        sa.Column('nao_conformidades', sa.Text(), nullable=True),
        sa.Column('plano_acao', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero', name='uq_auditorias_internas_numero')
    )
    op.create_index('idx_auditorias_internas_numero', 'auditorias_internas', ['numero'])
    op.create_index('idx_auditorias_resultado', 'auditorias_internas', ['resultado'])

    op.create_table(
        'revisoes_direcao',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('data_revisao', sa.Date(), nullable=False),
        sa.Column('participantes', sa.Text(), nullable=True),
        sa.Column('itens_analisados', sa.Text(), nullable=True),
        sa.Column('decisoes', sa.Text(), nullable=True),
        sa.Column('proximas_revisoes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_revisoes_direcao_data', 'revisoes_direcao', ['data_revisao'])


def downgrade() -> None:
    op.drop_index('idx_revisoes_direcao_data', 'revisoes_direcao')
    op.drop_table('revisoes_direcao')
    op.drop_index('idx_auditorias_resultado', 'auditorias_internas')
    op.drop_index('idx_auditorias_internas_numero', 'auditorias_internas')
    op.drop_table('auditorias_internas')
