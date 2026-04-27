"""Pedido status eventos - timeline para acompanhamento do comprador.

Revision ID: pe01_pedido_evt
Revises: a01bb670p6z2
Create Date: 2026-03-19

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "pe01_pedido_evt"
down_revision = "a01bb670p6z2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pedido_status_eventos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("tipo_evento", sa.String(length=50), nullable=False),
        sa.Column("status_codigo", sa.String(length=30), nullable=True),
        sa.Column("status_label", sa.String(length=100), nullable=True),
        sa.Column("actor_type", sa.String(length=30), nullable=False, server_default="sistema"),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["pedido_id"],
            ["pedidos_marketplace.id"],
            name="fk_pedido_status_eventos_pedido",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "actor_type IN ('sistema', 'loja', 'webhook')",
            name="ck_pedido_status_eventos_actor_type",
        ),
    )
    op.create_index("ix_pedido_status_eventos_pedido_id", "pedido_status_eventos", ["pedido_id"])
    op.create_index("ix_pedido_status_eventos_created_at", "pedido_status_eventos", ["created_at"])

    # Backfill: criar evento inicial para pedidos existentes (timeline a partir de agora)
    conn = op.get_bind()
    conn.execute(text("""
        INSERT INTO pedido_status_eventos (pedido_id, tipo_evento, status_codigo, status_label, actor_type, created_at)
        SELECT pm.id,
               CASE
                   WHEN pm.status_pedido = 'aguardando_pagamento' THEN 'pedido_criado'
                   WHEN pm.status_pedido = 'confirmado' AND pm.status_pagamento = 'pago' THEN 'pagamento_aprovado'
                   ELSE 'status_alterado'
               END,
               pm.status_pedido,
               COALESCE(
                   (SELECT spm.label FROM status_pedido_marketplace spm
                    WHERE spm.codigo = pm.status_pedido AND spm.ativo = true LIMIT 1),
                   REPLACE(pm.status_pedido, '_', ' ')
               ),
               'sistema',
               pm.created_at
        FROM pedidos_marketplace pm
    """))


def downgrade() -> None:
    op.drop_index("ix_pedido_status_eventos_created_at", table_name="pedido_status_eventos")
    op.drop_index("ix_pedido_status_eventos_pedido_id", table_name="pedido_status_eventos")
    op.drop_table("pedido_status_eventos")
