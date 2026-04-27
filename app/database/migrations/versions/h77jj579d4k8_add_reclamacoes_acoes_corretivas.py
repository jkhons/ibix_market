"""add reclamacoes acoes_corretivas ISO17025 5.8 5.11

Revision ID: h77jj579d4k8
Revises: c22ee924d9b3
Create Date: 2026-02-06

"""
import sqlalchemy as sa
from alembic import op

revision = 'h77jj579d4k8'
down_revision = 'c22ee924d9b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabela reclamacoes (ISO 17025 5.8)
    op.create_table(
        'reclamacoes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('numero', sa.String(50), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=True),
        sa.Column('certificado_id', sa.Integer(), nullable=True),
        sa.Column('processo_id', sa.Integer(), nullable=True),
        sa.Column('data_abertura', sa.Date(), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='aberta'),
        sa.Column('analise', sa.Text(), nullable=True),
        sa.Column('acao_tomada', sa.Text(), nullable=True),
        sa.Column('data_conclusao', sa.Date(), nullable=True),
        sa.Column('responsavel_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['certificado_id'], ['certificados.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['processo_id'], ['processos.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['responsavel_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero', name='uq_reclamacoes_numero')
    )
    op.create_index(op.f('idx_reclamacoes_numero'), 'reclamacoes', ['numero'])
    op.create_index(op.f('idx_reclamacoes_status'), 'reclamacoes', ['status'])
    op.create_index('idx_reclamacoes_cliente_id', 'reclamacoes', ['cliente_id'])
    op.create_index('idx_reclamacoes_certificado_id', 'reclamacoes', ['certificado_id'])
    op.create_index('idx_reclamacoes_processo_id', 'reclamacoes', ['processo_id'])

    # Tabela acoes_corretivas (ISO 17025 5.11)
    op.create_table(
        'acoes_corretivas',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('processo_id', sa.Integer(), nullable=False),
        sa.Column('nc_numero', sa.String(50), nullable=True),
        sa.Column('causa_raiz', sa.Text(), nullable=True),
        sa.Column('acao_planejada', sa.Text(), nullable=False),
        sa.Column('responsavel_id', sa.Integer(), nullable=True),
        sa.Column('data_prevista', sa.Date(), nullable=True),
        sa.Column('data_conclusao', sa.Date(), nullable=True),
        sa.Column('eficacia_verificada', sa.Boolean(), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['processo_id'], ['processos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['responsavel_id'], ['usuarios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_acoes_corretivas_processo_id', 'acoes_corretivas', ['processo_id'])
    op.create_index('idx_acoes_corretivas_responsavel_id', 'acoes_corretivas', ['responsavel_id'])


def downgrade() -> None:
    op.drop_index('idx_acoes_corretivas_responsavel_id', 'acoes_corretivas')
    op.drop_index('idx_acoes_corretivas_processo_id', 'acoes_corretivas')
    op.drop_table('acoes_corretivas')
    op.drop_index('idx_reclamacoes_processo_id', 'reclamacoes')
    op.drop_index('idx_reclamacoes_certificado_id', 'reclamacoes')
    op.drop_index('idx_reclamacoes_cliente_id', 'reclamacoes')
    op.drop_index('idx_reclamacoes_cliente_id', 'reclamacoes')
    op.drop_index(op.f('idx_reclamacoes_status'), 'reclamacoes')
    op.drop_index(op.f('idx_reclamacoes_numero'), 'reclamacoes')
    op.drop_table('reclamacoes')
