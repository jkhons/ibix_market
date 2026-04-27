"""Pagamentos marketplace: PaymentTransaction (pedido_id, tentativa), PaymentProviderConfig (conexão), WebhookEvent (rico), reserva_estoque_marketplace.

Revision ID: mp01_payments
Revises: mk04_politica
Create Date: 2026-03-10

Bloco 0 + Fase A (A1, A2, A3, A6). Executar com .venv ativo.
Tabelas payment_transactions, payment_provider_configs, webhook_events devem existir (branch ff55/z67bb aplicada).
"""
import sqlalchemy as sa
from alembic import op

revision = "mp01_payments"
down_revision = "mk04_politica"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A1 — payment_transactions: suporte a tentativa por pedido (marketplace)
    op.add_column(
        "payment_transactions",
        sa.Column("pedido_id", sa.Integer(), nullable=True, comment="FK pedidos_marketplace; contexto marketplace"),
    )
    op.add_column(
        "payment_transactions",
        sa.Column("provider_checkout_id", sa.String(200), nullable=True, comment="ID do checkout no provedor"),
    )
    op.add_column(
        "payment_transactions",
        sa.Column("attempt_number", sa.Integer(), nullable=True, server_default="1", comment="Número da tentativa no pedido"),
    )
    op.add_column(
        "payment_transactions",
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true", comment="Tentativa vigente (apenas uma True por pedido)"),
    )
    op.add_column(
        "payment_transactions",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "payment_transactions",
        sa.Column("provider_status", sa.String(50), nullable=True, comment="Status bruto do provedor"),
    )
    op.create_foreign_key(
        "fk_payment_transactions_pedido_id",
        "payment_transactions",
        "pedidos_marketplace",
        ["pedido_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_payment_transactions_pedido_id", "payment_transactions", ["pedido_id"])
    op.create_index("ix_payment_transactions_is_active", "payment_transactions", ["is_active"])

    # A2 — payment_provider_configs: conexão por loja/OAuth
    op.add_column(
        "payment_provider_configs",
        sa.Column("account_external_id", sa.String(200), nullable=True, comment="ID da conta no provedor (OAuth)"),
    )
    op.add_column(
        "payment_provider_configs",
        sa.Column("webhook_secret_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "payment_provider_configs",
        sa.Column("public_key_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "payment_provider_configs",
        sa.Column("metadata_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "payment_provider_configs",
        sa.Column("connection_status", sa.String(30), nullable=True, server_default="pending"),
    )
    op.add_column(
        "payment_provider_configs",
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "payment_provider_configs",
        sa.Column("last_error", sa.Text(), nullable=True),
    )

    # A3 — webhook_events: enriquecido para auditoria
    op.add_column(
        "webhook_events",
        sa.Column("event_type", sa.String(64), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("provider_event_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("provider_payment_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("payment_transaction_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("subscription_payment_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("signature_valid", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("normalized_status", sa.String(50), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("headers_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("query_params_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "webhook_events",
        sa.Column("processing_attempts", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "webhook_events",
        sa.Column("last_processing_error", sa.Text(), nullable=True),
    )

    # A6 — reserva_estoque_marketplace
    op.create_table(
        "reserva_estoque_marketplace",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("pedido_item_id", sa.Integer(), nullable=True),
        sa.Column("produto_cliente_id", sa.Integer(), nullable=True),
        sa.Column("anuncio_id", sa.Integer(), nullable=False),
        sa.Column("quantidade", sa.Numeric(12, 3), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="reserved", comment="reserved, committed, released"),
        sa.Column("reserved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reserved_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pedido_item_id"], ["pedido_itens_marketplace.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["produto_cliente_id"], ["produtos_cliente.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["anuncio_id"], ["anuncios_plataforma.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_reserva_estoque_marketplace_pedido_id", "reserva_estoque_marketplace", ["pedido_id"])
    op.create_index("ix_reserva_estoque_marketplace_status", "reserva_estoque_marketplace", ["status"])
    op.create_index("ix_reserva_estoque_marketplace_reserved_until", "reserva_estoque_marketplace", ["reserved_until"])


def downgrade() -> None:
    op.drop_index("ix_reserva_estoque_marketplace_reserved_until", "reserva_estoque_marketplace")
    op.drop_index("ix_reserva_estoque_marketplace_status", "reserva_estoque_marketplace")
    op.drop_index("ix_reserva_estoque_marketplace_pedido_id", "reserva_estoque_marketplace")
    op.drop_table("reserva_estoque_marketplace")

    op.drop_column("webhook_events", "last_processing_error")
    op.drop_column("webhook_events", "processing_attempts")
    op.drop_column("webhook_events", "error_message")
    op.drop_column("webhook_events", "query_params_json")
    op.drop_column("webhook_events", "headers_json")
    op.drop_column("webhook_events", "normalized_status")
    op.drop_column("webhook_events", "signature_valid")
    op.drop_column("webhook_events", "subscription_payment_id")
    op.drop_column("webhook_events", "payment_transaction_id")
    op.drop_column("webhook_events", "provider_payment_id")
    op.drop_column("webhook_events", "provider_event_id")
    op.drop_column("webhook_events", "event_type")

    op.drop_column("payment_provider_configs", "last_error")
    op.drop_column("payment_provider_configs", "last_validated_at")
    op.drop_column("payment_provider_configs", "connection_status")
    op.drop_column("payment_provider_configs", "metadata_json")
    op.drop_column("payment_provider_configs", "public_key_encrypted")
    op.drop_column("payment_provider_configs", "webhook_secret_encrypted")
    op.drop_column("payment_provider_configs", "account_external_id")

    op.drop_index("ix_payment_transactions_is_active", "payment_transactions")
    op.drop_index("ix_payment_transactions_pedido_id", "payment_transactions")
    op.drop_constraint("fk_payment_transactions_pedido_id", "payment_transactions", type_="foreignkey")
    op.drop_column("payment_transactions", "provider_status")
    op.drop_column("payment_transactions", "cancelled_at")
    op.drop_column("payment_transactions", "is_active")
    op.drop_column("payment_transactions", "attempt_number")
    op.drop_column("payment_transactions", "provider_checkout_id")
    op.drop_column("payment_transactions", "pedido_id")
