"""Fase 2 - precos_pdv, contrato_comercial, contrato_aditivos, divulgadores, divulgador_regras, codigos_desconto

Revision ID: nn33pp469v9
Revises: mm22oo358u8
Create Date: 2026-02-20

Plano consultoria PDV Etapas 2.1, 2.2, 2.5: estrutura comercial completa.
"""
import sqlalchemy as sa
from alembic import op

revision = "nn33pp469v9"
down_revision = "mm22oo358u8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "precos_pdv",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("valor_base_centavos", sa.Integer(), nullable=False, comment="Assinatura base (inclui 1 PDV) em centavos"),
        sa.Column("valor_pdv_adicional_centavos", sa.Integer(), nullable=False, comment="Valor de cada PDV adicional em centavos"),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False, comment="Data início da vigência"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        comment="Preços de licença PDV (valor_base + valor_pdv_adicional) em centavos",
    )
    op.create_index("ix_precos_pdv_ativo", "precos_pdv", ["ativo"])

    op.create_table(
        "contrato_comercial",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=True, comment="Null = indeterminado"),
        sa.Column("qtd_pdvs_contratados", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("valor_mensal_centavos", sa.Integer(), nullable=False, comment="Valor total mensal em centavos"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativo", comment="ativo, encerrado, cancelado"),
        comment="Contrato de assinatura SaaS por tenant",
    )
    op.create_index("ix_contrato_comercial_tenant_id", "contrato_comercial", ["tenant_id"])
    op.create_index("ix_contrato_comercial_tenant_status", "contrato_comercial", ["tenant_id", "status"])

    op.create_table(
        "contrato_aditivos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("contrato_id", sa.Integer(), sa.ForeignKey("contrato_comercial.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_aditivo", sa.Date(), nullable=False),
        sa.Column("qtd_pdvs_anterior", sa.Integer(), nullable=False),
        sa.Column("qtd_pdvs_nova", sa.Integer(), nullable=False),
        sa.Column("valor_anterior_centavos", sa.Integer(), nullable=False),
        sa.Column("valor_novo_centavos", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        comment="Aditivos ao contrato comercial SaaS",
    )
    op.create_index("ix_contrato_aditivos_contrato_id", "contrato_aditivos", ["contrato_id"])
    op.create_index("ix_contrato_aditivos_contrato_data", "contrato_aditivos", ["contrato_id", "data_aditivo"])

    op.create_table(
        "divulgadores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("cpf_cnpj", sa.String(20), nullable=True, comment="CPF ou CNPJ (opcional)"),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True),
        comment="Divulgadores/parceiros comerciais",
    )
    op.create_index("ix_divulgadores_ativo", "divulgadores", ["ativo"])

    op.create_table(
        "divulgador_regras",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("divulgador_id", sa.Integer(), sa.ForeignKey("divulgadores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("percentual_plano_ativo", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("recebe_primeira_parcela", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("percentual_comissao", sa.Integer(), nullable=False, server_default=sa.text("0")),
        comment="Regras de comissão do divulgador",
    )
    op.create_index("ix_divulgador_regras_divulgador_id", "divulgador_regras", ["divulgador_id"])

    op.create_table(
        "codigos_desconto",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False, unique=True),
        sa.Column("tipo_promocao", sa.String(50), nullable=False, comment="desconto_primeira_parcela, desconto_mensalidade, trial_estendido"),
        sa.Column("desconto_primeira_parcela_percent", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("desconto_mensalidade_percent", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("meses_desconto", sa.Integer(), nullable=True, comment="Meses de vigência (null=indefinido)"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("divulgador_id", sa.Integer(), sa.ForeignKey("divulgadores.id", ondelete="SET NULL"), nullable=True),
        comment="Códigos de desconto/promoção",
    )
    op.create_index("ix_codigos_desconto_codigo", "codigos_desconto", ["codigo"], unique=True)
    op.create_index("ix_codigos_desconto_ativo", "codigos_desconto", ["ativo"])
    op.create_index("ix_codigos_desconto_divulgador_id", "codigos_desconto", ["divulgador_id"])

    # Seed: preço padrão R$ 170 base + R$ 70/PDV adicional
    op.execute(
        "INSERT INTO precos_pdv (valor_base_centavos, valor_pdv_adicional_centavos, vigencia_inicio, ativo, created_at, updated_at) "
        "VALUES (17000, 7000, CURRENT_DATE, true, NOW(), NOW())"
    )


def downgrade() -> None:
    op.drop_table("codigos_desconto")
    op.drop_table("divulgador_regras")
    op.drop_table("divulgadores")
    op.drop_table("contrato_aditivos")
    op.drop_table("contrato_comercial")
    op.drop_table("precos_pdv")
