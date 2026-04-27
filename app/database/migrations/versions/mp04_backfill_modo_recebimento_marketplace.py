"""Backfill modo_recebimento em PaymentTransactions do marketplace.

Revision ID: mp04_modo_rep
Revises: pe01_pedido_evt
Create Date: 2026-03-19

Transações de marketplace (pedido_id NOT NULL) criadas antes da correção não tinham
modo_recebimento gravado. Este backfill define modo_recebimento='plataforma' para
transações com pedido_id preenchido e modo_recebimento NULL, desde que exista
Empresa com modo_recebimento='plataforma' para o cliente_id da transação.
Para transações cujo cliente não tem Empresa em modo plataforma, mantém NULL
( não entrarão no resumo de repasses).
"""
from alembic import op
from sqlalchemy import text

revision = "mp04_modo_rep"
down_revision = "pe01_pedido_evt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Transações marketplace (pedido_id NOT NULL) sem modo_recebimento:
    # backfill 'plataforma' (checkout usa plataforma quando Empresa em modo plataforma ou default)
    conn.execute(text("""
        UPDATE payment_transactions
        SET modo_recebimento = 'plataforma'
        WHERE pedido_id IS NOT NULL
          AND (modo_recebimento IS NULL OR modo_recebimento = '')
    """))


def downgrade() -> None:
    # Não reversível com segurança - não sabemos o valor original
    pass
