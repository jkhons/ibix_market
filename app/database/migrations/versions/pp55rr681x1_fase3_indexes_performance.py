"""Fase 3 - índices de performance para paginação (vendas, estoque, OS, aberturas, payments)

Revision ID: pp55rr681x1
Revises: oo44qq570w0
Create Date: 2026-02-20

Etapa 3.1: índices em colunas usadas em filtros e ORDER BY das listagens paginadas.
"""
from alembic import op

revision = "pp55rr681x1"
down_revision = "oo44qq570w0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_vendas_cliente_id", "vendas", ["cliente_id"], if_not_exists=True)
    op.create_index("ix_vendas_data_venda", "vendas", ["data_venda"], if_not_exists=True)
    op.create_index("ix_vendas_cliente_data", "vendas", ["cliente_id", "data_venda"], if_not_exists=True)
    op.create_index("ix_vendas_status", "vendas", ["status"], if_not_exists=True)

    op.create_index("ix_estoque_cliente_id", "estoque", ["cliente_id"], if_not_exists=True)

    op.create_index("ix_ordem_servico_cliente_id", "ordem_servico", ["cliente_id"], if_not_exists=True)
    op.create_index("ix_ordem_servico_status", "ordem_servico", ["status"], if_not_exists=True)

    op.create_index("ix_aberturas_caixa_pdv_id", "aberturas_caixa", ["pdv_id"], if_not_exists=True)

    op.create_index("ix_payment_transactions_created_at", "payment_transactions", ["created_at"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_payment_transactions_created_at", "payment_transactions", if_exists=True)
    op.drop_index("ix_aberturas_caixa_pdv_id", "aberturas_caixa", if_exists=True)
    op.drop_index("ix_ordem_servico_status", "ordem_servico", if_exists=True)
    op.drop_index("ix_ordem_servico_cliente_id", "ordem_servico", if_exists=True)
    op.drop_index("ix_estoque_cliente_id", "estoque", if_exists=True)
    op.drop_index("ix_vendas_status", "vendas", if_exists=True)
    op.drop_index("ix_vendas_cliente_data", "vendas", if_exists=True)
    op.drop_index("ix_vendas_data_venda", "vendas", if_exists=True)
    op.drop_index("ix_vendas_cliente_id", "vendas", if_exists=True)
