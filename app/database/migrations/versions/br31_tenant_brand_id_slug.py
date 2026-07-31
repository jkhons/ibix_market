"""Multi-brand Fase 3.1: tenant.brand_id + slug único por marca (expand-contract).

Revision ID: br31_tenant_brand_id_slug
Revises: br03_merge_multibrand
Create Date: 2026-06-18
"""
import sqlalchemy as sa
from alembic import op

revision = "br31_tenant_brand_id_slug"
down_revision = "br03_merge_multibrand"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    op.add_column(
        "tenants",
        sa.Column("brand_id", sa.Integer(), nullable=True, comment="Marca do tenant (Ibix, Solumática, …)"),
    )
    op.create_index("ix_tenants_brand_id", "tenants", ["brand_id"], unique=False)

    ibix_id = conn.execute(sa.text("SELECT id FROM brands WHERE slug = 'ibix' LIMIT 1")).scalar()
    if not ibix_id:
        raise RuntimeError("Marca Ibix não encontrada. Execute br01 antes de br31.")
    conn.execute(
        sa.text("UPDATE tenants SET brand_id = :bid WHERE brand_id IS NULL"),
        {"bid": ibix_id},
    )

    op.create_foreign_key(
        "fk_tenants_brand_id",
        "tenants",
        "brands",
        ["brand_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_unique_constraint(
        "uq_tenants_brand_slug",
        "tenants",
        ["brand_id", "slug"],
    )
    op.drop_constraint("uq_tenants_slug", "tenants", type_="unique")

    op.alter_column("tenants", "brand_id", nullable=False)


def downgrade() -> None:
    conn = op.get_bind()
    dupes = conn.execute(
        sa.text(
            """
            SELECT slug FROM tenants
            WHERE slug IS NOT NULL
            GROUP BY slug HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).fetchone()
    if dupes:
        raise RuntimeError(
            "Downgrade br31 bloqueado: slugs duplicados entre marcas. Resolva antes de reverter."
        )

    op.create_unique_constraint("uq_tenants_slug", "tenants", ["slug"])
    op.drop_constraint("uq_tenants_brand_slug", "tenants", type_="unique")
    op.drop_constraint("fk_tenants_brand_id", "tenants", type_="foreignkey")
    op.drop_index("ix_tenants_brand_id", table_name="tenants")
    op.drop_column("tenants", "brand_id")
