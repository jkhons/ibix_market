"""Fase 3 - Estabelecimentos fiscais, venda_pagamentos (fracionamento), movimentos_caixa (sangria/suprimento).

Revision ID: ee44gg570w0
Revises: dd33ff469v9
Create Date: 2026-02-18

- 3.1.1 estabelecimentos_fiscais: fiscal por estabelecimento (cliente_id), cnpj, ie, crt, certificado, regime, serie_nfe, aliquotas_uf.
- 3.2 venda_pagamentos: múltiplos pagamentos por venda (fracionamento).
- 3.2 movimentos_caixa: sangria e suprimento por abertura_caixa.
"""
import sqlalchemy as sa
from alembic import op

revision = "ee44gg570w0"
down_revision = "dd33ff469v9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 3.1.1 Estabelecimentos fiscais (multi-estabelecimento por CA)
    op.create_table(
        "estabelecimentos_fiscais",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False, comment="Estabelecimento (clientes.id)"),
        sa.Column("cnpj", sa.String(18), nullable=False),
        sa.Column("ie", sa.String(20), nullable=True),
        sa.Column("crt", sa.Integer(), nullable=True, comment="1=Simples, 2=Simples excesso, 3=Regime normal"),
        sa.Column("certificado_digital_path", sa.String(512), nullable=True),
        sa.Column("regime_tributario", sa.String(50), nullable=True),
        sa.Column("serie_nfe", sa.String(10), nullable=True, server_default="1"),
        sa.Column("aliquotas_uf", sa.Text(), nullable=True, comment="JSON: alíquotas por UF"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_estabelecimentos_fiscais_cliente_id", "estabelecimentos_fiscais", ["cliente_id"])
    op.create_index("ix_estabelecimentos_fiscais_cnpj", "estabelecimentos_fiscais", ["cnpj"])

    # 3.2 Venda pagamentos (fracionamento: múltiplos pagamentos por venda)
    op.create_table(
        "venda_pagamentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("venda_id", sa.Integer(), nullable=False),
        sa.Column("forma", sa.String(30), nullable=False, comment="dinheiro, cartao_credito, cartao_debito, pix, boleto, transferencia, vale, crediario"),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=True, server_default="confirmado", comment="pendente, confirmado, estornado"),
        sa.Column("id_externo", sa.String(100), nullable=True, comment="ID no gateway/adquirente"),
        sa.Column("observacao", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["venda_id"], ["vendas.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_venda_pagamentos_venda_id", "venda_pagamentos", ["venda_id"])

    # 3.2 Movimentos de caixa (sangria e suprimento)
    op.create_table(
        "movimentos_caixa",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("abertura_caixa_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False, comment="sangria, suprimento"),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("observacao", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["abertura_caixa_id"], ["aberturas_caixa.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_movimentos_caixa_abertura_caixa_id", "movimentos_caixa", ["abertura_caixa_id"])


def downgrade() -> None:
    op.drop_index("ix_movimentos_caixa_abertura_caixa_id", table_name="movimentos_caixa")
    op.drop_table("movimentos_caixa")
    op.drop_index("ix_venda_pagamentos_venda_id", table_name="venda_pagamentos")
    op.drop_table("venda_pagamentos")
    op.drop_index("ix_estabelecimentos_fiscais_cnpj", table_name="estabelecimentos_fiscais")
    op.drop_index("ix_estabelecimentos_fiscais_cliente_id", table_name="estabelecimentos_fiscais")
    op.drop_table("estabelecimentos_fiscais")
