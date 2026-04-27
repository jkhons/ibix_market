"""Senha mestra por estabelecimento (Fase 5.2 - política obrigatória no plano).

Revision ID: jj99ll025b5
Revises: ii88kk914a4
Create Date: 2026-02-18

- Tabela senha_mestra_estabelecimento: uma senha mestra por cliente_id (estabelecimento),
  hash, expira_em (validade temporária). Uso: sangria/suprimento, descontos acima do limite,
  cancelamento de venda. Nunca hardcoded; log de uso em audit_log.
"""
import sqlalchemy as sa
from alembic import op

revision = "jj99ll025b5"
down_revision = "ii88kk914a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "senha_mestra_estabelecimento",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False, comment="Estabelecimento (clientes.id); uma senha por estabelecimento"),
        sa.Column("senha_hash", sa.String(255), nullable=False, comment="Hash da senha mestra (bcrypt)"),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=True, comment="Validade temporária; null = até próxima alteração"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("cliente_id", name="uq_senha_mestra_estabelecimento_cliente_id"),
    )
    op.create_index("ix_senha_mestra_estabelecimento_cliente_id", "senha_mestra_estabelecimento", ["cliente_id"])


def downgrade() -> None:
    op.drop_index("ix_senha_mestra_estabelecimento_cliente_id", table_name="senha_mestra_estabelecimento")
    op.drop_table("senha_mestra_estabelecimento")
