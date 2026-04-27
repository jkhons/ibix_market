"""Logística local: entregadores, entregas_marketplace, entrega_eventos.

Revision ID: lg01_entregas_marketplace
Revises: mp03_idempotency
Create Date: 2026-03-10

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "lg01_entregas_marketplace"
down_revision = "mp03_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================
    # TABELA: entregadores
    # tenant_id NULL = entregador da plataforma; preenchido = entregador privado/vinculado ao tenant
    # =========================================
    op.create_table(
        "entregadores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("telefone", sa.String(length=30), nullable=True),
        sa.Column("cpf", sa.String(length=20), nullable=True),
        sa.Column("tipo_veiculo", sa.String(length=20), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ativo"),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("cidade", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('ativo', 'bloqueado', 'pendente')",
            name="ck_entregadores_status",
        ),
        sa.CheckConstraint(
            "tipo_veiculo IS NULL OR tipo_veiculo IN ('moto', 'carro', 'utilitario')",
            name="ck_entregadores_tipo_veiculo",
        ),
        sa.UniqueConstraint("email", name="uq_entregadores_email"),
    )
    op.create_index("ix_entregadores_tenant_id", "entregadores", ["tenant_id"])
    op.create_index("ix_entregadores_status", "entregadores", ["status"])
    op.create_index("ix_entregadores_cidade", "entregadores", ["cidade"])

    # =========================================
    # TABELA: entregas_marketplace
    # =========================================
    op.create_table(
        "entregas_marketplace",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("entregador_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="aguardando_publicacao"),
        sa.Column("valor_frete", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("tipo_veiculo_aceito", sa.String(length=20), nullable=True),
        sa.Column("nome_retirada", sa.String(length=150), nullable=True),
        sa.Column("telefone_retirada", sa.String(length=30), nullable=True),
        sa.Column("endereco_retirada_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("nome_destinatario", sa.String(length=150), nullable=True),
        sa.Column("telefone_destinatario", sa.String(length=30), nullable=True),
        sa.Column("endereco_entrega_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("aceita_ate_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publicada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aceita_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retirada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("saiu_para_entrega_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entregue_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("codigo_confirmacao", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos_marketplace.id"], name="fk_entregas_marketplace_pedido", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entregador_id"], ["entregadores.id"], name="fk_entregas_marketplace_entregador", ondelete="SET NULL"),
        sa.UniqueConstraint("pedido_id", name="uq_entregas_marketplace_pedido_id"),
        sa.CheckConstraint(
            "status IN ("
            "'aguardando_publicacao', 'disponivel', 'aceita', 'em_retirada', "
            "'retirada', 'em_rota', 'entregue', 'cancelada', 'expirada', 'falha_entrega')",
            name="ck_entregas_marketplace_status",
        ),
        sa.CheckConstraint(
            "tipo_veiculo_aceito IS NULL OR tipo_veiculo_aceito IN ('moto', 'carro', 'utilitario', 'qualquer')",
            name="ck_entregas_marketplace_tipo_veiculo_aceito",
        ),
    )
    op.create_index("ix_entregas_marketplace_status", "entregas_marketplace", ["status"])
    op.create_index("ix_entregas_marketplace_tenant_id", "entregas_marketplace", ["tenant_id"])
    op.create_index("ix_entregas_marketplace_entregador_id", "entregas_marketplace", ["entregador_id"])
    op.create_index("ix_entregas_marketplace_publicada_em", "entregas_marketplace", ["publicada_em"])
    op.create_index("ix_entregas_marketplace_aceita_ate_em", "entregas_marketplace", ["aceita_ate_em"])

    # =========================================
    # TABELA: entrega_eventos
    # =========================================
    op.create_table(
        "entrega_eventos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entrega_id", sa.Integer(), nullable=False),
        sa.Column("tipo_evento", sa.String(length=50), nullable=False),
        sa.Column("actor_type", sa.String(length=30), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["entrega_id"], ["entregas_marketplace.id"], name="fk_entrega_eventos_entrega", ondelete="CASCADE"),
        sa.CheckConstraint(
            "actor_type IN ('sistema', 'tenant_usuario', 'entregador')",
            name="ck_entrega_eventos_actor_type",
        ),
    )
    op.create_index("ix_entrega_eventos_entrega_id", "entrega_eventos", ["entrega_id"])
    op.create_index("ix_entrega_eventos_created_at", "entrega_eventos", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_entrega_eventos_created_at", table_name="entrega_eventos")
    op.drop_index("ix_entrega_eventos_entrega_id", table_name="entrega_eventos")
    op.drop_table("entrega_eventos")

    op.drop_index("ix_entregas_marketplace_aceita_ate_em", table_name="entregas_marketplace")
    op.drop_index("ix_entregas_marketplace_publicada_em", table_name="entregas_marketplace")
    op.drop_index("ix_entregas_marketplace_entregador_id", table_name="entregas_marketplace")
    op.drop_index("ix_entregas_marketplace_tenant_id", table_name="entregas_marketplace")
    op.drop_index("ix_entregas_marketplace_status", table_name="entregas_marketplace")
    op.drop_table("entregas_marketplace")

    op.drop_index("ix_entregadores_cidade", table_name="entregadores")
    op.drop_index("ix_entregadores_status", table_name="entregadores")
    op.drop_index("ix_entregadores_tenant_id", table_name="entregadores")
    op.drop_table("entregadores")
