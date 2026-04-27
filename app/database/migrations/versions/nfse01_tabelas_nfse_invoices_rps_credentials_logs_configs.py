"""Fase 1 NFS-e: tabelas nfse_invoices, nfse_rps, nfse_credentials, nfse_message_logs, nfse_provider_configs

Revision ID: nfse01_tbl
Revises: nfse00_ibge
Create Date: 2026-03-02

Conforme MODULO_FATURAMENT_V2.MD Parte V (DDL). Adaptado para PostgreSQL.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "nfse01_tbl"
down_revision = "nfse00_ibge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    is_pg = conn.dialect.name == "postgresql"

    # nfse_invoices (documento universal)
    op.create_table(
        "nfse_invoices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=True),
        sa.Column("origin_type", sa.String(20), nullable=False),
        sa.Column("origin_id", sa.Integer(), nullable=True),
        sa.Column("municipio_prestacao_ibge", sa.Integer(), nullable=False),
        sa.Column("data_competencia", sa.Date(), nullable=False),
        sa.Column("descricao_servico", sa.Text(), nullable=True),
        sa.Column("item_lista_servico", sa.String(20), nullable=True),
        sa.Column("cnae", sa.String(20), nullable=True),
        sa.Column("valor_servicos", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("valor_deducoes", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("base_iss", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("aliquota_iss", sa.Numeric(9, 4), nullable=False, server_default="0"),
        sa.Column("valor_iss", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("iss_retido", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("valor_iss_retido", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("provider", sa.String(20), nullable=False, server_default="NACIONAL"),
        sa.Column("external_id", sa.String(120), nullable=True),
        sa.Column("numero_nfse", sa.String(60), nullable=True),
        sa.Column("codigo_verificacao", sa.String(80), nullable=True),
        sa.Column("url_consulta", sa.String(500), nullable=True),
        sa.Column("data_emissao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(40), nullable=True),
        sa.Column("last_error_msg", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_nfse_invoices_tenant_empresa_status", "nfse_invoices", ["tenant_id", "empresa_id", "status"])
    op.create_index("ix_nfse_invoices_tenant_numero", "nfse_invoices", ["tenant_id", "numero_nfse"])
    op.create_index("uq_nfse_origin", "nfse_invoices", ["tenant_id", "origin_type", "origin_id"], unique=True)

    # nfse_rps
    op.create_table(
        "nfse_rps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("nfse_invoice_id", sa.Integer(), nullable=True),
        sa.Column("serie", sa.String(10), nullable=False, server_default="1"),
        sa.Column("numero", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="RESERVED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["nfse_invoice_id"], ["nfse_invoices.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_nfse_rps_tenant_empresa_status", "nfse_rps", ["tenant_id", "empresa_id", "status"])
    op.create_index("uq_nfse_rps", "nfse_rps", ["tenant_id", "empresa_id", "serie", "numero"], unique=True)

    # nfse_credentials
    op.create_table(
        "nfse_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="A1_PFX"),
        sa.Column("pfx_blob", sa.LargeBinary(), nullable=False),
        sa.Column("pfx_password", sa.LargeBinary(), nullable=False),
        sa.Column("cert_serial", sa.String(80), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_nfse_credentials_tenant_empresa_status", "nfse_credentials", ["tenant_id", "empresa_id", "status"])

    # nfse_provider_configs
    if is_pg:
        op.create_table(
            "nfse_provider_configs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(20), nullable=False, server_default="NACIONAL"),
            sa.Column("municipio_ibge", sa.Integer(), nullable=True),
            sa.Column("environment", sa.String(20), nullable=False, server_default="HOMOLOG"),
            sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        )
    else:
        op.create_table(
            "nfse_provider_configs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(20), nullable=False, server_default="NACIONAL"),
            sa.Column("municipio_ibge", sa.Integer(), nullable=True),
            sa.Column("environment", sa.String(20), nullable=False, server_default="HOMOLOG"),
            sa.Column("config_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        )
    op.create_index("ix_nfse_provider_configs_lookup", "nfse_provider_configs", ["tenant_id", "empresa_id", "provider", "municipio_ibge"])

    # nfse_message_logs (depende de nfse_invoices)
    op.create_table(
        "nfse_message_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("nfse_invoice_id", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("payload_redacted", sa.Text(), nullable=True),
        sa.Column("response_redacted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["nfse_invoice_id"], ["nfse_invoices.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_nfse_message_logs_invoice_created", "nfse_message_logs", ["tenant_id", "nfse_invoice_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_nfse_message_logs_invoice_created", table_name="nfse_message_logs")
    op.drop_table("nfse_message_logs")
    op.drop_index("ix_nfse_provider_configs_lookup", table_name="nfse_provider_configs")
    op.drop_table("nfse_provider_configs")
    op.drop_index("ix_nfse_credentials_tenant_empresa_status", table_name="nfse_credentials")
    op.drop_table("nfse_credentials")
    op.drop_index("uq_nfse_rps", table_name="nfse_rps")
    op.drop_index("ix_nfse_rps_tenant_empresa_status", table_name="nfse_rps")
    op.drop_table("nfse_rps")
    op.drop_index("uq_nfse_origin", table_name="nfse_invoices")
    op.drop_index("ix_nfse_invoices_tenant_numero", table_name="nfse_invoices")
    op.drop_index("ix_nfse_invoices_tenant_empresa_status", table_name="nfse_invoices")
    op.drop_table("nfse_invoices")
