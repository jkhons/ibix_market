"""add procedimentos_metodo treinamentos_competencia ISO17025

Revision ID: c22ee924d9b3
Revises: b11de913c8a2
Create Date: 2026-02-06

"""
import sqlalchemy as sa
from alembic import op

revision = 'c22ee924d9b3'
down_revision = 'g66ii468d3j7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabela procedimentos_metodo (ISO 17025 7.2)
    op.create_table(
        'procedimentos_metodo',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('codigo', sa.String(50), nullable=False),
        sa.Column('nome', sa.String(255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('norma_ref', sa.String(100), nullable=True),
        sa.Column('versao', sa.String(20), nullable=True),
        sa.Column('data_aprovacao', sa.Date(), nullable=True),
        sa.Column('aprovado_por_id', sa.Integer(), nullable=True),
        sa.Column('categoria', sa.String(50), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['aprovado_por_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo', name='uq_procedimentos_metodo_codigo')
    )
    op.create_index(op.f('idx_procedimentos_metodo_codigo'), 'procedimentos_metodo', ['codigo'])
    op.create_index(op.f('idx_procedimentos_metodo_categoria'), 'procedimentos_metodo', ['categoria'])
    op.create_index(op.f('idx_procedimentos_metodo_ativo'), 'procedimentos_metodo', ['ativo'])

    # FK procedimento_metodo_id em processo_balanca_calibracao
    op.add_column('processo_balanca_calibracao', sa.Column('procedimento_metodo_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_processo_balanca_procedimento_metodo',
        'processo_balanca_calibracao',
        'procedimentos_metodo',
        ['procedimento_metodo_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Tabela treinamentos_competencia (ISO 17025 6.2)
    op.create_table(
        'treinamentos_competencia',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('aux_cadastro_id', sa.Integer(), nullable=False),
        sa.Column('procedimento_metodo_id', sa.Integer(), nullable=True),
        sa.Column('tipo_ensaio', sa.String(50), nullable=True, comment='Fallback: indicacao, excentricidade, mobilidade'),
        sa.Column('data_treinamento', sa.Date(), nullable=False),
        sa.Column('data_validade', sa.Date(), nullable=True),
        sa.Column('status', sa.String(30), nullable=True, comment='aprovado, pendente, reprovado'),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['aux_cadastro_id'], ['aux_cadastros.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['procedimento_metodo_id'], ['procedimentos_metodo.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('idx_treinamentos_aux_cadastro'), 'treinamentos_competencia', ['aux_cadastro_id'])
    op.create_index(op.f('idx_treinamentos_data_validade'), 'treinamentos_competencia', ['data_validade'])


def downgrade() -> None:
    op.drop_index(op.f('idx_treinamentos_data_validade'), 'treinamentos_competencia')
    op.drop_index(op.f('idx_treinamentos_aux_cadastro'), 'treinamentos_competencia')
    op.drop_table('treinamentos_competencia')
    op.drop_constraint('fk_processo_balanca_procedimento_metodo', 'processo_balanca_calibracao', type_='foreignkey')
    op.drop_column('processo_balanca_calibracao', 'procedimento_metodo_id')
    op.drop_index(op.f('idx_procedimentos_metodo_ativo'), 'procedimentos_metodo')
    op.drop_index(op.f('idx_procedimentos_metodo_categoria'), 'procedimentos_metodo')
    op.drop_index(op.f('idx_procedimentos_metodo_codigo'), 'procedimentos_metodo')
    op.drop_table('procedimentos_metodo')
