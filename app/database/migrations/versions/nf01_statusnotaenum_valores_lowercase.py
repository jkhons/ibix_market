"""Garante valores lowercase no enum statusnotaenum (autorizado, cancelado, etc.)

Revision ID: nf01fiscal
Revises: t99uu791h9q3
Create Date: 2026-03-02

Adiciona ao enum statusnotaenum os valores em minúsculo usados pelo modelo
StatusNotaEnum (autorizado, cancelado, rejeitado, denegado, pendente), para
compatibilidade com aplicação que persiste status após envio/cancelamento.
"""
from alembic import op

revision = "nf01fiscal"
down_revision = "t99uu791h9q3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        for val in ("autorizado", "cancelado", "rejeitado", "denegado", "pendente"):
            op.execute(f"ALTER TYPE statusnotaenum ADD VALUE IF NOT EXISTS '{val}'")


def downgrade() -> None:
    # PostgreSQL não permite remover valores de enum; downgrade é no-op
    pass
