"""Motor tributário ICMS: tabela regras_fiscais_icms e colunas de auditoria em notas_fiscais_itens.

Revision ID: regras_fisc_icms
Revises: prod_cli_csosn
Create Date: 2026-03-12

Regras fiscais parametrizadas por empresa. Motor resolve CFOP, CST/CSOSN, origem e ICMS por item.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "regras_fisc_icms"
down_revision = "prod_cli_csosn"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Tabela regras_fiscais_icms
    op.create_table(
        "regras_fiscais_icms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ordem_prioridade", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("crt", sa.Integer(), nullable=True),
        sa.Column("tipo_operacao", sa.String(30), nullable=True),
        sa.Column("tipo_destinatario", sa.String(20), nullable=True),
        sa.Column("uf_destinatario", sa.String(2), nullable=True),
        sa.Column("ncm_prefix", sa.String(4), nullable=True),
        sa.Column("ncm_exato", sa.String(8), nullable=True),
        sa.Column("cest", sa.String(20), nullable=True),
        sa.Column("cfop_filtro", sa.String(4), nullable=True),
        sa.Column("finalidade_emissao", sa.String(50), nullable=True),
        sa.Column("consumidor_final", sa.Boolean(), nullable=True),
        sa.Column("contribuinte_icms", sa.Boolean(), nullable=True),
        sa.Column("cfop", sa.String(4), nullable=False),
        sa.Column("origem_mercadoria", sa.Integer(), nullable=False),
        sa.Column("cst_icms", sa.String(5), nullable=True),
        sa.Column("csosn", sa.String(5), nullable=True),
        sa.Column("aliquota_icms", sa.Numeric(7, 4), nullable=False, server_default="0"),
        sa.Column("modalidade_bc_icms", sa.String(2), nullable=True),
        sa.Column("percentual_reducao_bc", sa.Numeric(7, 4), nullable=True),
        sa.Column("gera_icms_st", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("aliquota_icms_st", sa.Numeric(7, 4), nullable=True),
        sa.Column("modalidade_bc_icms_st", sa.String(2), nullable=True),
        sa.Column("percentual_mva_st", sa.Numeric(7, 4), nullable=True),
        sa.Column("permite_credito_icms", sa.Boolean(), nullable=True),
        sa.Column("vigencia_inicio", sa.Date(), nullable=True),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.Column("observacao_interna", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_regra_empresa", "regras_fiscais_icms", ["empresa_id"])
    op.create_index("idx_regra_prioridade", "regras_fiscais_icms", ["empresa_id", "ativo", "ordem_prioridade"])
    op.create_index("idx_regra_ncm", "regras_fiscais_icms", ["empresa_id", "ncm_exato", "ncm_prefix"])

    # 2. Colunas em notas_fiscais_itens
    op.add_column(
        "notas_fiscais_itens",
        sa.Column("regra_fiscal_icms_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_notas_fiscais_itens_regra_fiscal",
        "notas_fiscais_itens",
        "regras_fiscais_icms",
        ["regra_fiscal_icms_id"],
        ["id"],
        ondelete="SET NULL",
    )

    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.add_column(
            "notas_fiscais_itens",
            sa.Column("motor_contexto_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
        op.add_column(
            "notas_fiscais_itens",
            sa.Column("motor_resultado_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
    else:
        op.add_column(
            "notas_fiscais_itens",
            sa.Column("motor_contexto_json", sa.Text(), nullable=True),
        )
        op.add_column(
            "notas_fiscais_itens",
            sa.Column("motor_resultado_json", sa.Text(), nullable=True),
        )

    op.add_column(
        "notas_fiscais_itens",
        sa.Column("motor_versao", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notas_fiscais_itens", "motor_versao")
    op.drop_column("notas_fiscais_itens", "motor_resultado_json")
    op.drop_column("notas_fiscais_itens", "motor_contexto_json")
    op.drop_constraint("fk_notas_fiscais_itens_regra_fiscal", "notas_fiscais_itens", type_="foreignkey")
    op.drop_column("notas_fiscais_itens", "regra_fiscal_icms_id")

    op.drop_index("idx_regra_ncm", table_name="regras_fiscais_icms")
    op.drop_index("idx_regra_prioridade", table_name="regras_fiscais_icms")
    op.drop_index("idx_regra_empresa", table_name="regras_fiscais_icms")
    op.drop_table("regras_fiscais_icms")
