"""Fase 0 NFS-e: municipio_ibge (empresa, clientes), empresa_id (ordem_servico), default_empresa_id e ca_cliente_id (tenants)

Revision ID: nfse00_ibge
Revises: nf01fiscal
Create Date: 2026-03-02

Conforme MODULO_FATURAMENT_V2.MD Parte VI e plano_faturamento_nfse_implementacao.plan.md Fase 0.
"""
import sqlalchemy as sa
from alembic import op

revision = "nfse00_ibge"
down_revision = "nf01fiscal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) IBGE em empresa e clientes
    op.add_column(
        "empresa",
        sa.Column("municipio_ibge", sa.Integer(), nullable=True, comment="Código IBGE do município do prestador (emissor NFS-e)"),
    )
    op.add_column(
        "clientes",
        sa.Column("municipio_ibge", sa.Integer(), nullable=True, comment="Código IBGE do município do tomador"),
    )

    # 2) Emissor na OS e padrões do tenant
    op.add_column(
        "tenants",
        sa.Column("default_empresa_id", sa.Integer(), nullable=True, comment="Empresa emissora padrão para NFS-e de subscription"),
    )
    op.add_column(
        "tenants",
        sa.Column("ca_cliente_id", sa.Integer(), nullable=True, comment="Cliente CA (tomador padrão) para NFS-e de subscription"),
    )
    op.add_column(
        "ordem_servico",
        sa.Column("empresa_id", sa.Integer(), nullable=True, comment="Emissor da NFS-e ao faturar a OS"),
    )

    op.create_foreign_key(
        "fk_tenants_default_empresa",
        "tenants",
        "empresa",
        ["default_empresa_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_tenants_ca_cliente",
        "tenants",
        "clientes",
        ["ca_cliente_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_ordem_servico_empresa",
        "ordem_servico",
        "empresa",
        ["empresa_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_tenants_default_empresa_id", "tenants", ["default_empresa_id"])
    op.create_index("ix_tenants_ca_cliente_id", "tenants", ["ca_cliente_id"])
    op.create_index("ix_ordem_servico_empresa_id", "ordem_servico", ["empresa_id"])


def downgrade() -> None:
    op.drop_index("ix_ordem_servico_empresa_id", table_name="ordem_servico")
    op.drop_constraint("fk_ordem_servico_empresa", "ordem_servico", type_="foreignkey")
    op.drop_column("ordem_servico", "empresa_id")

    op.drop_index("ix_tenants_ca_cliente_id", table_name="tenants")
    op.drop_index("ix_tenants_default_empresa_id", table_name="tenants")
    op.drop_constraint("fk_tenants_ca_cliente", "tenants", type_="foreignkey")
    op.drop_constraint("fk_tenants_default_empresa", "tenants", type_="foreignkey")
    op.drop_column("tenants", "ca_cliente_id")
    op.drop_column("tenants", "default_empresa_id")

    op.drop_column("clientes", "municipio_ibge")
    op.drop_column("empresa", "municipio_ibge")
