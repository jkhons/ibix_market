"""Multi-brand Fase 3.2: índices compostos para queries quentes (tenant/brand).

Revision ID: br33_performance_indexes
Revises: br32_consumidor_modules
Create Date: 2026-06-18

Gatilho particionamento (documentado): se vendas/pedidos_marketplace > ~10M linhas ou
seq_scan dominante em EXPLAIN, avaliar PARTITION BY RANGE (created_at) — fora do escopo atual.
"""
from alembic import op

revision = "br33_performance_indexes"
down_revision = "br32_consumidor_modules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_tenants_brand_ativo",
        "tenants",
        ["brand_id", "ativo"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_pedidos_cliente_data_pedido",
        "pedidos",
        ["cliente_id", "data_pedido"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_pedidos_cliente_status",
        "pedidos",
        ["cliente_id", "status"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_pedidos_marketplace_tenant_created",
        "pedidos_marketplace",
        ["tenant_id", "created_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_usuarios_tenant_ativo",
        "usuarios",
        ["tenant_id", "ativo"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_usuarios_tenant_ativo", table_name="usuarios", if_exists=True)
    op.drop_index("ix_pedidos_marketplace_tenant_created", table_name="pedidos_marketplace", if_exists=True)
    op.drop_index("ix_pedidos_cliente_status", table_name="pedidos", if_exists=True)
    op.drop_index("ix_pedidos_cliente_data_pedido", table_name="pedidos", if_exists=True)
    op.drop_index("ix_tenants_brand_ativo", table_name="tenants", if_exists=True)
