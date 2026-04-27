"""Empresa: modo_recebimento + taxas plataforma; tabela repasses.

Adiciona campo modo_recebimento (direto/plataforma) na empresa,
campos de taxa da plataforma, e tabela repasses para controle
de transferências da plataforma para o CA.

Revision ID: pg01_modo_repasse
Revises: cupom_tenant
Create Date: 2026-03-16

"""
import sqlalchemy as sa
from alembic import op

revision = "pg01_modo_repasse"
down_revision = "cupom_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("empresa", sa.Column(
        "modo_recebimento", sa.String(20), nullable=False, server_default="plataforma",
        comment="'direto' = CA recebe na própria conta; 'plataforma' = plataforma recebe e repassa",
    ))
    op.add_column("empresa", sa.Column(
        "taxa_plataforma_percentual", sa.Numeric(5, 2), nullable=True,
        comment="Taxa percentual da plataforma sobre vendas (ex: 5.00 = 5%)",
    ))
    op.add_column("empresa", sa.Column(
        "taxa_plataforma_valor_fixo", sa.Numeric(10, 2), nullable=True,
        comment="Taxa fixa da plataforma por transação (ex: 2.50 = R$2,50)",
    ))

    op.create_table(
        "repasses",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("cliente_id", sa.Integer, sa.ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("valor_bruto", sa.Numeric(12, 2), nullable=False),
        sa.Column("valor_taxa", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("valor_liquido", sa.Numeric(12, 2), nullable=False),
        sa.Column("periodo_inicio", sa.Date, nullable=False),
        sa.Column("periodo_fim", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("data_repasse", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comprovante", sa.Text, nullable=True),
        sa.Column("observacao", sa.Text, nullable=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_repasses_status", "repasses", ["status"])
    op.create_index("ix_repasses_periodo", "repasses", ["periodo_inicio", "periodo_fim"])

    op.add_column("payment_transactions", sa.Column(
        "modo_recebimento", sa.String(20), nullable=True,
        comment="'direto' = CA recebeu; 'plataforma' = plataforma recebeu (para repasse)",
    ))


def downgrade() -> None:
    op.drop_column("payment_transactions", "modo_recebimento")
    op.drop_table("repasses")
    op.drop_column("empresa", "taxa_plataforma_valor_fixo")
    op.drop_column("empresa", "taxa_plataforma_percentual")
    op.drop_column("empresa", "modo_recebimento")
