"""Orçamento/OS: rastreio de origem da venda (venda_origens + orcamento_origem_id).

Revision ID: or04_venda_origens_rastreio
Revises: br36_ca_pii_visualizar
Create Date: 2026-06-18
"""
import sqlalchemy as sa
from alembic import op

from app.core.rls import RLS_TENANT_POLICY

revision = "or04_venda_origens_rastreio"
down_revision = "br36_ca_pii_visualizar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ordem_servico",
        sa.Column("orcamento_origem_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_ordem_servico_orcamento_origem_id",
        "ordem_servico",
        "orcamentos",
        ["orcamento_origem_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_ordem_servico_cliente_orcamento_origem",
        "ordem_servico",
        ["cliente_id", "orcamento_origem_id"],
    )

    op.create_table(
        "venda_origens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("venda_id", sa.Integer(), sa.ForeignKey("vendas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo_origem", sa.String(30), nullable=False),
        sa.Column("documento_id", sa.Integer(), nullable=True),
        sa.Column("documento_ref", sa.String(100), nullable=True),
        sa.Column("papel", sa.String(20), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "venda_id",
            "papel",
            "tipo_origem",
            "documento_id",
            name="uq_venda_origens_venda_papel_tipo_doc",
        ),
    )
    op.create_index("ix_venda_origens_tenant_venda", "venda_origens", ["tenant_id", "venda_id"])
    op.create_index(
        "ix_venda_origens_tenant_tipo_doc",
        "venda_origens",
        ["tenant_id", "tipo_origem", "documento_id"],
    )

    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE venda_origens ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE venda_origens FORCE ROW LEVEL SECURITY"))
    conn.execute(sa.text(RLS_TENANT_POLICY.format(table="venda_origens")))

    # Backfill ordem_servico.orcamento_origem_id
    conn.execute(
        sa.text(
            """
            UPDATE ordem_servico os
            SET orcamento_origem_id = o.id
            FROM orcamentos o
            WHERE o.convertido_em_ordem_servico_id = os.id
              AND os.orcamento_origem_id IS NULL
            """
        )
    )

    # Backfill venda_origens a partir de FKs existentes
    conn.execute(
        sa.text(
            """
            INSERT INTO venda_origens (tenant_id, venda_id, tipo_origem, documento_id, documento_ref, papel, usuario_id)
            SELECT u.tenant_id, v.id, 'orcamento', v.orcamento_id, o.numero_orcamento, 'imediata', v.vendedor_id
            FROM vendas v
            JOIN usuarios u ON u.id = v.vendedor_id
            JOIN orcamentos o ON o.id = v.orcamento_id
            WHERE v.orcamento_id IS NOT NULL AND u.tenant_id IS NOT NULL
            ON CONFLICT ON CONSTRAINT uq_venda_origens_venda_papel_tipo_doc DO NOTHING
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO venda_origens (tenant_id, venda_id, tipo_origem, documento_id, documento_ref, papel, usuario_id)
            SELECT u.tenant_id, v.id, 'orcamento', v.orcamento_id, o.numero_orcamento, 'raiz', v.vendedor_id
            FROM vendas v
            JOIN usuarios u ON u.id = v.vendedor_id
            JOIN orcamentos o ON o.id = v.orcamento_id
            WHERE v.orcamento_id IS NOT NULL AND u.tenant_id IS NOT NULL
            ON CONFLICT ON CONSTRAINT uq_venda_origens_venda_papel_tipo_doc DO NOTHING
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO venda_origens (tenant_id, venda_id, tipo_origem, documento_id, documento_ref, papel, usuario_id)
            SELECT u.tenant_id, v.id, 'ordem_servico', v.ordem_servico_id, os.codigo, 'imediata', v.vendedor_id
            FROM vendas v
            JOIN usuarios u ON u.id = v.vendedor_id
            JOIN ordem_servico os ON os.id = v.ordem_servico_id
            WHERE v.ordem_servico_id IS NOT NULL AND u.tenant_id IS NOT NULL
            ON CONFLICT ON CONSTRAINT uq_venda_origens_venda_papel_tipo_doc DO NOTHING
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO venda_origens (tenant_id, venda_id, tipo_origem, documento_id, documento_ref, papel, usuario_id)
            SELECT u.tenant_id, v.id, 'orcamento', os.orcamento_origem_id, o.numero_orcamento, 'raiz', v.vendedor_id
            FROM vendas v
            JOIN usuarios u ON u.id = v.vendedor_id
            JOIN ordem_servico os ON os.id = v.ordem_servico_id
            JOIN orcamentos o ON o.id = os.orcamento_origem_id
            WHERE v.ordem_servico_id IS NOT NULL
              AND os.orcamento_origem_id IS NOT NULL
              AND u.tenant_id IS NOT NULL
            ON CONFLICT ON CONSTRAINT uq_venda_origens_venda_papel_tipo_doc DO NOTHING
            """
        )
    )
    # Propagar orcamento_id em vendas via OS
    conn.execute(
        sa.text(
            """
            UPDATE vendas v
            SET orcamento_id = os.orcamento_origem_id
            FROM ordem_servico os
            WHERE v.ordem_servico_id = os.id
              AND v.orcamento_id IS NULL
              AND os.orcamento_origem_id IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP POLICY IF EXISTS rls_venda_origens_tenant ON venda_origens"))
    op.drop_table("venda_origens")
    op.drop_index("ix_ordem_servico_cliente_orcamento_origem", table_name="ordem_servico")
    op.drop_constraint("fk_ordem_servico_orcamento_origem_id", "ordem_servico", type_="foreignkey")
    op.drop_column("ordem_servico", "orcamento_origem_id")
