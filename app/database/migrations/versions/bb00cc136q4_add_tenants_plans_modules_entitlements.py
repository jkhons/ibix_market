"""add tenants, plans, modules, tenant_entitlements and usuarios.tenant_id

Revision ID: bb00cc136q4
Revises: c33dd035p5m2
Create Date: 2026-02-08

SaaS: tenants, plans, modules, tenant_entitlements; usuarios.tenant_id.
"""
import sqlalchemy as sa
from alembic import op

revision = "bb00cc136q4"
down_revision = "c33dd035p5m2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # plans (sem FK)
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("descricao", sa.String(500), nullable=True),
        sa.Column("preco", sa.Numeric(12, 2), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_plans_slug"),
        comment="Catálogo de planos SaaS",
    )
    op.create_index("ix_plans_id", "plans", ["id"])
    op.create_index("ix_plans_slug", "plans", ["slug"])
    op.create_index("ix_plans_ativo", "plans", ["ativo"])

    # modules (sem FK)
    op.create_table(
        "modules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("descricao", sa.String(500), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_modules_slug"),
        comment="Catálogo de módulos SaaS",
    )
    op.create_index("ix_modules_id", "modules", ["id"])
    op.create_index("ix_modules_slug", "modules", ["slug"])
    op.create_index("ix_modules_ativo", "modules", ["ativo"])

    # tenants (FK plan_id)
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=True),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
        sa.UniqueConstraint("external_id", name="uq_tenants_external_id"),
        comment="Tenant SaaS: organização que assina planos",
    )
    op.create_index("ix_tenants_id", "tenants", ["id"])
    op.create_index("ix_tenants_slug", "tenants", ["slug"])
    op.create_index("ix_tenants_external_id", "tenants", ["external_id"])
    op.create_index("ix_tenants_plan_id", "tenants", ["plan_id"])
    op.create_index("ix_tenants_ativo", "tenants", ["ativo"])

    # tenant_entitlements
    op.create_table(
        "tenant_entitlements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ativo"),
        sa.Column("limits", sa.String(500), nullable=True),
        sa.Column("vigencia_inicio", sa.Date(), nullable=True),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "module_id", name="uq_tenant_entitlements_tenant_module"),
        comment="Entitlements: módulos liberados por tenant",
    )
    op.create_index("ix_tenant_entitlements_id", "tenant_entitlements", ["id"])
    op.create_index("ix_tenant_entitlements_tenant_id", "tenant_entitlements", ["tenant_id"])
    op.create_index("ix_tenant_entitlements_module_id", "tenant_entitlements", ["module_id"])
    op.create_index("ix_tenant_entitlements_tenant_status", "tenant_entitlements", ["tenant_id", "status"])

    # usuarios.tenant_id
    op.add_column("usuarios", sa.Column("tenant_id", sa.Integer(), nullable=True, comment="Tenant SaaS"))
    op.create_foreign_key(
        "fk_usuarios_tenant_id_tenants",
        "usuarios",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_usuarios_tenant_id", "usuarios", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_usuarios_tenant_id", "usuarios")
    op.drop_constraint("fk_usuarios_tenant_id_tenants", "usuarios", type_="foreignkey")
    op.drop_column("usuarios", "tenant_id")

    op.drop_index("ix_tenant_entitlements_tenant_status", "tenant_entitlements")
    op.drop_index("ix_tenant_entitlements_module_id", "tenant_entitlements")
    op.drop_index("ix_tenant_entitlements_tenant_id", "tenant_entitlements")
    op.drop_index("ix_tenant_entitlements_id", "tenant_entitlements")
    op.drop_table("tenant_entitlements")

    op.drop_index("ix_tenants_ativo", "tenants")
    op.drop_index("ix_tenants_plan_id", "tenants")
    op.drop_index("ix_tenants_external_id", "tenants")
    op.drop_index("ix_tenants_slug", "tenants")
    op.drop_index("ix_tenants_id", "tenants")
    op.drop_table("tenants")

    op.drop_index("ix_modules_ativo", "modules")
    op.drop_index("ix_modules_slug", "modules")
    op.drop_index("ix_modules_id", "modules")
    op.drop_table("modules")

    op.drop_index("ix_plans_ativo", "plans")
    op.drop_index("ix_plans_slug", "plans")
    op.drop_index("ix_plans_id", "plans")
    op.drop_table("plans")
