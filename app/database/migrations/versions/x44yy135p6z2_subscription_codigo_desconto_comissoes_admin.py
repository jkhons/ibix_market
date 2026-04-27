"""subscription codigo_desconto_id e tabela comissoes_administrador

Revision ID: x44yy135p6z2
Revises: ww33xx137n3x1
Create Date: 2026-03-02

- subscriptions.codigo_desconto_id (FK codigos_desconto, nullable)
- comissoes_administrador (comissão do Administrador por pagamento, uma por payment_id)
"""
import sqlalchemy as sa
from alembic import op

revision = "x44yy135p6z2"
down_revision = "ww33xx137n3x1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("codigo_desconto_id", sa.Integer(), nullable=True, comment="Código usado no cadastro (vínculo Admin/divulgador e comissão)"),
    )
    op.create_foreign_key(
        "fk_subscriptions_codigo_desconto_id",
        "subscriptions",
        "codigos_desconto",
        ["codigo_desconto_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_subscriptions_codigo_desconto_id", "subscriptions", ["codigo_desconto_id"])

    op.create_table(
        "comissoes_administrador",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id_administrador", sa.Integer(), nullable=False),
        sa.Column("valor_mensalidade_centavos", sa.Integer(), nullable=False),
        sa.Column("percentual_comissao", sa.Integer(), nullable=False),
        sa.Column("valor_comissao_centavos", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("pago_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id_administrador"], ["usuarios.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("payment_id", name="uq_comissoes_administrador_payment_id"),
        comment="Comissão do Administrador por pagamento (uma por payment_id)",
    )
    op.create_index("ix_comissoes_administrador_payment_id", "comissoes_administrador", ["payment_id"])
    op.create_index("ix_comissoes_administrador_usuario_id_administrador", "comissoes_administrador", ["usuario_id_administrador"])
    op.create_index("ix_comissoes_administrador_status", "comissoes_administrador", ["status"])
    op.create_index("ix_comissoes_administrador_usuario_status", "comissoes_administrador", ["usuario_id_administrador", "status"])


def downgrade() -> None:
    op.drop_index("ix_comissoes_administrador_usuario_status", "comissoes_administrador")
    op.drop_index("ix_comissoes_administrador_status", "comissoes_administrador")
    op.drop_index("ix_comissoes_administrador_usuario_id_administrador", "comissoes_administrador")
    op.drop_index("ix_comissoes_administrador_payment_id", "comissoes_administrador")
    op.drop_table("comissoes_administrador")

    op.drop_index("ix_subscriptions_codigo_desconto_id", "subscriptions")
    op.drop_constraint("fk_subscriptions_codigo_desconto_id", "subscriptions", type_="foreignkey")
    op.drop_column("subscriptions", "codigo_desconto_id")
