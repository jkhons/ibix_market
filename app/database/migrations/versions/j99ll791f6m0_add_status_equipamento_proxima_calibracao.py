"""add status_equipamento proxima_calibracao aux_cadastros ISO17025 6.4

Revision ID: j99ll791f6m0
Revises: i88kk680e5l9
Create Date: 2026-02-06

"""
import sqlalchemy as sa
from alembic import op

revision = 'j99ll791f6m0'
down_revision = 'i88kk680e5l9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('aux_cadastros', sa.Column('status_equipamento', sa.String(30), nullable=True))
    op.add_column('aux_cadastros', sa.Column('proxima_calibracao', sa.Date(), nullable=True))
    op.create_index('idx_aux_cadastros_status_equipamento', 'aux_cadastros', ['status_equipamento'])
    op.create_index('idx_aux_cadastros_proxima_calibracao', 'aux_cadastros', ['proxima_calibracao'])


def downgrade() -> None:
    op.drop_index('idx_aux_cadastros_proxima_calibracao', 'aux_cadastros')
    op.drop_index('idx_aux_cadastros_status_equipamento', 'aux_cadastros')
    op.drop_column('aux_cadastros', 'proxima_calibracao')
    op.drop_column('aux_cadastros', 'status_equipamento')
