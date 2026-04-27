"""Fase 3.3 - Módulo de Pagamentos: payment_provider_configs, split_rules, payment_transactions, transaction_splits, payment_logs.

Revision ID: ff55hh681x1
Revises: ee44gg570w0
Create Date: 2026-02-18

Estabelecimento = cliente_id (clientes.id).
"""
import sqlalchemy as sa
from alembic import op

revision = "ff55hh681x1"
down_revision = "ee44gg570w0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # payment_provider_configs: por estabelecimento (cliente_id)
    op.create_table(
        "payment_provider_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False, comment="Estabelecimento (clientes.id)"),
        sa.Column("provider_code", sa.String(50), nullable=False, comment="pagbank, cielo, stone, efi, mercadopago"),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True, comment="Credenciais criptografadas (JSON)"),
        sa.Column("fee_configs", sa.Text(), nullable=True, comment="JSON: taxas por método"),
        sa.Column("routing_rules", sa.Text(), nullable=True, comment="JSON: prioridade, métodos habilitados"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("test_mode", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_payment_provider_configs_cliente_id", "payment_provider_configs", ["cliente_id"])
    op.create_index("ix_payment_provider_configs_provider_code", "payment_provider_configs", ["provider_code"])

    # split_rules: regras de repasse por nível hierárquico
    op.create_table(
        "split_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False, comment="Estabelecimento ao qual a regra se aplica"),
        sa.Column("rule_type", sa.String(30), nullable=False, comment="fixed_percentage, fixed_value, tiered"),
        sa.Column("recipient_type", sa.String(30), nullable=False, comment="super_admin, admin, cliente_admin, estabelecimento"),
        sa.Column("recipient_id", sa.Integer(), nullable=True, comment="ID do destinatário (admin_id, cliente_id, etc.)"),
        sa.Column("percentage", sa.Numeric(8, 4), nullable=True),
        sa.Column("fixed_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("applies_to", sa.Text(), nullable=True, comment="JSON: payment_methods, min/max value"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_split_rules_cliente_id", "split_rules", ["cliente_id"])

    # payment_transactions: transações unificadas
    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False, comment="UUID público da transação"),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("venda_id", sa.Integer(), nullable=True),
        sa.Column("pdv_id", sa.Integer(), nullable=True),
        sa.Column("provider_code", sa.String(50), nullable=True),
        sa.Column("provider_transaction_id", sa.String(100), nullable=True),
        sa.Column("provider_response", sa.Text(), nullable=True, comment="JSON auditoria"),
        sa.Column("payment_method", sa.String(30), nullable=False, comment="credit, debit, pix, boleto, cash, transfer"),
        sa.Column("payment_submethod", sa.String(50), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("installments", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, comment="pending, processing, authorized, paid, failed, refunded, cancelled"),
        sa.Column("status_history", sa.Text(), nullable=True, comment="JSON"),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconciliation_status", sa.String(20), nullable=True, server_default="pending", comment="pending, matched, divergence"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_payment_transactions_uuid"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["venda_id"], ["vendas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pdv_id"], ["pdvs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_payment_transactions_uuid", "payment_transactions", ["uuid"])
    op.create_index("ix_payment_transactions_cliente_id", "payment_transactions", ["cliente_id"])
    op.create_index("ix_payment_transactions_status", "payment_transactions", ["status"])
    op.create_index("ix_payment_transactions_venda_id", "payment_transactions", ["venda_id"])

    # transaction_splits: valores distribuídos por transação
    op.create_table(
        "transaction_splits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("recipient_type", sa.String(30), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=True),
        sa.Column("original_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("fee_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", comment="pending, settled, failed"),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["transaction_id"], ["payment_transactions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_transaction_splits_transaction_id", "transaction_splits", ["transaction_id"])

    # payment_logs: auditoria de comunicação com provedores
    op.create_table(
        "payment_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        sa.Column("provider_code", sa.String(50), nullable=True),
        sa.Column("request_url", sa.String(512), nullable=True),
        sa.Column("request_headers", sa.Text(), nullable=True),
        sa.Column("request_body", sa.Text(), nullable=True),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["transaction_id"], ["payment_transactions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_payment_logs_transaction_id", "payment_logs", ["transaction_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_logs_transaction_id", table_name="payment_logs")
    op.drop_table("payment_logs")
    op.drop_index("ix_transaction_splits_transaction_id", table_name="transaction_splits")
    op.drop_table("transaction_splits")
    op.drop_index("ix_payment_transactions_venda_id", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_status", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_cliente_id", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_uuid", table_name="payment_transactions")
    op.drop_table("payment_transactions")
    op.drop_index("ix_split_rules_cliente_id", table_name="split_rules")
    op.drop_table("split_rules")
    op.drop_index("ix_payment_provider_configs_provider_code", table_name="payment_provider_configs")
    op.drop_index("ix_payment_provider_configs_cliente_id", table_name="payment_provider_configs")
    op.drop_table("payment_provider_configs")
