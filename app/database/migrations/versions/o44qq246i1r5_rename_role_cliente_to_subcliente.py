"""rename role Cliente to Subcliente (terminologia: subcliente gerenciado pelo Cliente Administrador)

Revision ID: o44qq246i1r5
Revises: n33pp135h0q4
Create Date: 2026-02-08

A role 'Cliente' passa a se chamar 'Subcliente' em todo o sistema.
"""
from alembic import op
from sqlalchemy import text

revision = "o44qq246i1r5"
down_revision = "n33pp135h0q4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("UPDATE roles SET nome = 'Subcliente', updated_at = NOW() WHERE nome = 'Cliente'"))
    # Garantir que a role Subcliente existe (caso Cliente não existia)
    r = conn.execute(text("SELECT 1 FROM roles WHERE nome = 'Subcliente'")).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO roles (nome, descricao, ativo, created_at, updated_at)
                VALUES ('Subcliente', 'Subcliente do sistema; gerenciado pelo Cliente Administrador.', true, NOW(), NOW())
            """)
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("UPDATE roles SET nome = 'Cliente', updated_at = NOW() WHERE nome = 'Subcliente'"))
