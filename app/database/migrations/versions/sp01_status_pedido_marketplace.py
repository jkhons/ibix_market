"""Tabela status_pedido_marketplace (lista global de status configurável pelo Super Admin) e seed mínimo.

Revision ID: sp01_status_mk
Revises: lg02_seed_entregador
Create Date: 2026-03-17

Sem dados mockados: seed apenas dos códigos necessários para compatibilidade com valores já usados no sistema.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "sp01_status_mk"
down_revision = "lg02_seed_entregador"
branch_labels = None
depends_on = None

STATUS_SEED = [
    ("aguardando_pagamento", "Aguardando pagamento", 0),
    ("confirmado", "Confirmado", 1),
    ("preparando", "Preparando", 2),
    ("enviado", "Enviado", 3),
    ("entregue", "Entregue", 4),
    ("cancelado", "Cancelado", 5),
]


def upgrade() -> None:
    op.create_table(
        "status_pedido_marketplace",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("codigo", sa.String(30), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_status_pedido_marketplace_codigo", "status_pedido_marketplace", ["codigo"], unique=True)

    conn = op.get_bind()
    for codigo, label, ordem in STATUS_SEED:
        r = conn.execute(text("SELECT 1 FROM status_pedido_marketplace WHERE codigo = :c"), {"c": codigo}).fetchone()
        if not r:
            conn.execute(
                text("""
                    INSERT INTO status_pedido_marketplace (codigo, label, ordem, ativo, created_at, updated_at)
                    VALUES (:codigo, :label, :ordem, true, NOW(), NOW())
                """),
                {"codigo": codigo, "label": label, "ordem": ordem},
            )


def downgrade() -> None:
    op.drop_index("ix_status_pedido_marketplace_codigo", table_name="status_pedido_marketplace")
    op.drop_table("status_pedido_marketplace")
