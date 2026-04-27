"""Merge heads: fiscal_corrigir_itens_fat e nfe_tent_env.

Revision ID: merge_fiscal_heads
Revises: fiscal_corrigir_itens_fat, nfe_tent_env
Create Date: 2026-03-12

Unifica os dois heads para permitir alembic upgrade head.
"""

revision = "merge_fiscal_heads"
down_revision = ("fiscal_corrigir_itens_fat", "nfe_tent_env")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
