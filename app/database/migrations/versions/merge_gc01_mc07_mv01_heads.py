"""Merge heads: gc01 (Google CSE), mc07 (categoria automação), mv01 (marketing vitrine).

Revision ID: merge_gc01_mc07_mv01
Revises: gc01_google_cse_quota, mc07_categoria_automacao, mv01_marketing_vitrine
Create Date: 2026-03-26

"""

revision = "merge_gc01_mc07_mv01"
down_revision = ("gc01_google_cse_quota", "mc07_categoria_automacao", "mv01_marketing_vitrine")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
