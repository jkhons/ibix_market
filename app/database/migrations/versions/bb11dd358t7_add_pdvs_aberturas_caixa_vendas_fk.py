"""add pdvs, aberturas_caixa e vendas.pdv_id/abertura_caixa_id (Fase 1 - Plano PDV Hierarquia).

Revision ID: bb11dd358t7
Revises: aa00cc247s6
Create Date: 2026-02-18

- Tabela pdvs: terminal por estabelecimento (cliente_id), UNIQUE(identificador, cliente_id).
- Tabela aberturas_caixa: turno por PDV (pdv_id, usuario_id, valor_inicial, status).
- vendas.pdv_id e vendas.abertura_caixa_id (nullable, FK).
"""
import sqlalchemy as sa
from alembic import op

revision = "bb11dd358t7"
down_revision = "aa00cc247s6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabela pdvs
    op.create_table(
        "pdvs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False, comment="Estabelecimento/loja ao qual o PDV pertence"),
        sa.Column("identificador", sa.String(50), nullable=False, comment="Ex.: CAIXA-01, PDV-01"),
        sa.Column("localizacao", sa.String(255), nullable=True, comment="Descrição do local"),
        sa.Column("ip_local", sa.String(45), nullable=True, comment="IP da estação"),
        sa.Column("mac_address", sa.String(17), nullable=True, comment="MAC do equipamento"),
        sa.Column("versao_software", sa.String(50), nullable=True, comment="Versão do software PDV"),
        sa.Column("ultimo_acesso", sa.DateTime(timezone=True), nullable=True, comment="Último acesso registrado"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativo", comment="ativo, inativo, manutencao"),
        sa.Column("configuracoes_hardware", sa.Text(), nullable=True, comment="JSON: impressora, gaveta, leitor, etc."),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("identificador", "cliente_id", name="uq_pdvs_identificador_cliente_id"),
    )
    op.create_index("ix_pdvs_cliente_id", "pdvs", ["cliente_id"])

    # Tabela aberturas_caixa
    op.create_table(
        "aberturas_caixa",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("pdv_id", sa.Integer(), nullable=False, comment="PDV em que o caixa foi aberto"),
        sa.Column("usuario_id", sa.Integer(), nullable=True, comment="Operador que abriu o caixa"),
        sa.Column("data_abertura", sa.DateTime(timezone=True), nullable=False, comment="Data/hora abertura"),
        sa.Column("data_fechamento", sa.DateTime(timezone=True), nullable=True, comment="Data/hora fechamento"),
        sa.Column("valor_inicial", sa.Numeric(12, 2), nullable=False, server_default="0", comment="Valor inicial do caixa"),
        sa.Column("valor_final", sa.Numeric(12, 2), nullable=True, comment="Valor ao fechar"),
        sa.Column("status", sa.String(20), nullable=False, server_default="aberta", comment="aberta, fechada"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pdv_id"], ["pdvs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_aberturas_caixa_pdv_id", "aberturas_caixa", ["pdv_id"])
    op.create_index("ix_aberturas_caixa_usuario_id", "aberturas_caixa", ["usuario_id"])

    # vendas: pdv_id e abertura_caixa_id
    op.add_column(
        "vendas",
        sa.Column("pdv_id", sa.Integer(), nullable=True, comment="PDV onde a venda foi realizada"),
    )
    op.add_column(
        "vendas",
        sa.Column("abertura_caixa_id", sa.Integer(), nullable=True, comment="Abertura de caixa (turno) vinculada à venda"),
    )
    op.create_foreign_key(
        "fk_vendas_pdv_id",
        "vendas",
        "pdvs",
        ["pdv_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_vendas_abertura_caixa_id",
        "vendas",
        "aberturas_caixa",
        ["abertura_caixa_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_vendas_pdv_id", "vendas", ["pdv_id"])
    op.create_index("ix_vendas_abertura_caixa_id", "vendas", ["abertura_caixa_id"])


def downgrade() -> None:
    op.drop_index("ix_vendas_abertura_caixa_id", table_name="vendas")
    op.drop_index("ix_vendas_pdv_id", table_name="vendas")
    op.drop_constraint("fk_vendas_abertura_caixa_id", "vendas", type_="foreignkey")
    op.drop_constraint("fk_vendas_pdv_id", "vendas", type_="foreignkey")
    op.drop_column("vendas", "abertura_caixa_id")
    op.drop_column("vendas", "pdv_id")

    op.drop_index("ix_aberturas_caixa_usuario_id", table_name="aberturas_caixa")
    op.drop_index("ix_aberturas_caixa_pdv_id", table_name="aberturas_caixa")
    op.drop_table("aberturas_caixa")

    op.drop_index("ix_pdvs_cliente_id", table_name="pdvs")
    op.drop_table("pdvs")
