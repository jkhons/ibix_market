"""Caixas por empresa fiscal; aberturas_caixa.caixa_id; remove pdvs e vendas.pdv_id.

Revision ID: cx01_caixas_remove_pdvs
Revises: fc01_fornecedor_cnpj_uq
"""
import sqlalchemy as sa
from alembic import op

revision = "cx01_caixas_remove_pdvs"
down_revision = "fc01_fornecedor_cnpj_uq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    op.create_table(
        "caixas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False, comment="Empresa fiscal dona do caixa"),
        sa.Column("identificador", sa.String(80), nullable=False, comment="Nome do caixa lógico"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("_legacy_pdv_id", sa.Integer(), nullable=True, comment="Migração: id antigo em pdvs"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("empresa_id", "identificador", name="uq_caixas_empresa_identificador"),
        sa.UniqueConstraint("_legacy_pdv_id", name="uq_caixas_legacy_pdv"),
    )
    op.create_index("ix_caixas_empresa_id", "caixas", ["empresa_id"])

    r = conn.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM pdvs p
            WHERE NOT EXISTS (
              SELECT 1 FROM empresa e
              WHERE e.cliente_id = p.cliente_id AND e.ativo IS TRUE
            )
            """
        )
    )
    orphan = r.scalar() or 0
    if int(orphan) > 0:
        raise RuntimeError(
            "Migração cx01: existem pdvs sem empresa fiscal ativa para o cliente_id. "
            "Corrija cadastros em /fiscal/empresa antes de migrar."
        )

    conn.execute(
        sa.text(
            """
            INSERT INTO caixas (created_at, updated_at, empresa_id, identificador, ativo, _legacy_pdv_id)
            SELECT p.created_at, p.updated_at, sub.empresa_id, p.identificador,
                   CASE WHEN lower(trim(p.status)) = 'ativo' THEN true ELSE false END,
                   p.id
            FROM pdvs p
            INNER JOIN (
              SELECT DISTINCT ON (e.cliente_id) e.id AS empresa_id, e.cliente_id
              FROM empresa e
              WHERE e.ativo IS TRUE
              ORDER BY e.cliente_id, e.id
            ) sub ON sub.cliente_id = p.cliente_id
            """
        )
    )

    op.add_column("aberturas_caixa", sa.Column("caixa_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_aberturas_caixa_caixa_id",
        "aberturas_caixa",
        "caixas",
        ["caixa_id"],
        ["id"],
        ondelete="CASCADE",
    )
    conn.execute(
        sa.text(
            """
            UPDATE aberturas_caixa ab
            SET caixa_id = c.id
            FROM caixas c
            WHERE c._legacy_pdv_id = ab.pdv_id
            """
        )
    )
    r2 = conn.execute(sa.text("SELECT COUNT(*) FROM aberturas_caixa WHERE caixa_id IS NULL"))
    if (r2.scalar() or 0) > 0:
        raise RuntimeError("Migração cx01: aberturas_caixa com caixa_id NULL após mapeamento.")

    op.alter_column("aberturas_caixa", "caixa_id", existing_type=sa.Integer(), nullable=False)

    op.execute("ALTER TABLE aberturas_caixa DROP CONSTRAINT IF EXISTS aberturas_caixa_pdv_id_fkey")
    op.drop_index("ix_aberturas_caixa_pdv_id", table_name="aberturas_caixa", if_exists=True)
    op.drop_column("aberturas_caixa", "pdv_id")

    op.add_column("payment_transactions", sa.Column("caixa_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_payment_transactions_caixa_id",
        "payment_transactions",
        "caixas",
        ["caixa_id"],
        ["id"],
        ondelete="SET NULL",
    )
    conn.execute(
        sa.text(
            """
            UPDATE payment_transactions pt
            SET caixa_id = c.id
            FROM caixas c
            WHERE pt.pdv_id IS NOT NULL AND c._legacy_pdv_id = pt.pdv_id
            """
        )
    )
    op.execute("ALTER TABLE payment_transactions DROP CONSTRAINT IF EXISTS payment_transactions_pdv_id_fkey")
    op.drop_column("payment_transactions", "pdv_id")

    op.drop_constraint("fk_vendas_pdv_id", "vendas", type_="foreignkey")
    op.drop_index("ix_vendas_pdv_id", table_name="vendas", if_exists=True)
    op.drop_column("vendas", "pdv_id")

    op.drop_table("pdvs")
    op.drop_constraint("uq_caixas_legacy_pdv", "caixas", type_="unique")
    op.drop_column("caixas", "_legacy_pdv_id")


def downgrade() -> None:
    raise RuntimeError("Downgrade cx01_caixas_remove_pdvs não suportado.")
