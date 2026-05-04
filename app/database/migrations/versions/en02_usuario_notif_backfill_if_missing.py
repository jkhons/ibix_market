"""Garante usuario_notificacoes em bancos que aplicaram en01 antes de nt01 existir no grafo.

Revision ID: en02_usuario_notif_backfill_if_missing
Revises: en01_entregador_docs_pagamento_merge
Create Date: 2026-04-30

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = "en02_usuario_notif_backfill_if_missing"
down_revision = "en01_entregador_docs_pagamento_merge"
branch_labels = None
depends_on = None


def _table_exists(conn, name: str) -> bool:
    r = conn.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :t"),
        {"t": name},
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "usuario_notificacoes"):
        return

    op.create_table(
        "usuario_notificacoes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(length=60), nullable=False),
        sa.Column("ref_id", sa.Integer(), nullable=True),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("icone", sa.String(length=40), nullable=True),
        sa.Column("cor", sa.String(length=20), nullable=True),
        sa.Column("dados_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("lida", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("lida_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("usuario_id", "tipo", "ref_id", name="uq_usuario_notif_user_tipo_ref"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usuario_notificacoes_usuario_id", "usuario_notificacoes", ["usuario_id"])
    op.create_index("ix_usuario_notificacoes_tenant_id", "usuario_notificacoes", ["tenant_id"])
    op.create_index("ix_usuario_notificacoes_tipo", "usuario_notificacoes", ["tipo"])
    op.create_index("ix_usuario_notificacoes_ref_id", "usuario_notificacoes", ["ref_id"])
    op.create_index("ix_usuario_notificacoes_lida", "usuario_notificacoes", ["lida"])


def downgrade() -> None:
    pass
