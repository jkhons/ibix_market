"""Tabela status_repasse e coluna repasse_status_id em payment_transactions.

Revision ID: rs01_status_rep
Revises: mp04_modo_rep
Create Date: 2026-03-19

Status de repasse por transação (Aguardando Repasse, Repasse Feito, etc.)
com sigla padronizada (5 caracteres) para exibição em badge.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "rs01_status_rep"
down_revision = "mp04_modo_rep"
branch_labels = None
depends_on = None

STATUS_SEED = [
    ("Aguardando Repasse", "AGUAR", 1),
    ("Repasse Feito", "FEITO", 2),
    ("Repasse Cancelado", "CANCE", 3),
    ("Repasse não concluído", "NCONC", 4),
    ("Repasse estornado", "ESTOR", 5),
]


def upgrade() -> None:
    op.create_table(
        "status_repasse",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("sigla", sa.String(5), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_status_repasse_sigla", "status_repasse", ["sigla"], unique=True)

    conn = op.get_bind()
    for nome, sigla, ordem in STATUS_SEED:
        r = conn.execute(text("SELECT 1 FROM status_repasse WHERE sigla = :s"), {"s": sigla}).fetchone()
        if not r:
            conn.execute(
                text("""
                    INSERT INTO status_repasse (nome, sigla, ordem, ativo, created_at, updated_at)
                    VALUES (:nome, :sigla, :ordem, true, NOW(), NOW())
                """),
                {"nome": nome, "sigla": sigla, "ordem": ordem},
            )

    op.add_column(
        "payment_transactions",
        sa.Column(
            "repasse_status_id",
            sa.Integer(),
            sa.ForeignKey("status_repasse.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="Status de repasse (só para modo_recebimento=plataforma)",
        ),
    )

    conn.execute(text("""
        UPDATE payment_transactions
        SET repasse_status_id = (SELECT id FROM status_repasse WHERE sigla = 'AGUAR' LIMIT 1)
        WHERE modo_recebimento = 'plataforma'
          AND status IN ('paid', 'authorized')
          AND repasse_status_id IS NULL
    """))


def downgrade() -> None:
    op.drop_column("payment_transactions", "repasse_status_id")
    op.drop_index("ix_status_repasse_sigla", table_name="status_repasse")
    op.drop_table("status_repasse")
