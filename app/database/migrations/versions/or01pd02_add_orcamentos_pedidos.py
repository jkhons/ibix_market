"""Módulo Orçamento e Pedido: tabelas orcamentos, orcamento_itens, pedidos, pedido_itens, pedido_faturamento, pedido_historico, reserva_estoque; notas_fiscais.pedido_id.

Revision ID: or01pd02
Revises: vv22ww024k2t7
Create Date: 2026-02-28

Conforme plano módulo Orçamento e Pedido: FKs/ondelete/UNIQUE/índices da seção 2.3.
"""
import sqlalchemy as sa
from alembic import op

revision = "or01pd02"
down_revision = "vv22ww024k2t7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. orcamentos (sem convertido_em_pedido_id - FK para pedidos será adicionada após criar pedidos)
    op.create_table(
        "orcamentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False, comment="Estabelecimento que emite"),
        sa.Column("vendedor_id", sa.Integer(), nullable=True),
        sa.Column("destinatario_id", sa.Integer(), nullable=True, comment="Cliente final/destinatário do orçamento"),
        sa.Column("numero_orcamento", sa.String(50), nullable=False),
        sa.Column("data_validade", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="rascunho"),
        sa.Column("subtotal", sa.Numeric(15, 2), nullable=True),
        sa.Column("desconto", sa.Numeric(15, 2), nullable=True),
        sa.Column("acrescimo", sa.Numeric(15, 2), nullable=True),
        sa.Column("total", sa.Numeric(15, 2), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("condicoes_pagamento", sa.Text(), nullable=True),
        sa.Column("data_conversao", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vendedor_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["destinatario_id"], ["clientes.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_orcamentos_cliente_id", "orcamentos", ["cliente_id"])
    op.create_index("ix_orcamentos_status", "orcamentos", ["status"])
    op.create_index("ix_orcamentos_data_validade", "orcamentos", ["data_validade"])
    op.create_unique_constraint("uq_orcamentos_cliente_numero", "orcamentos", ["cliente_id", "numero_orcamento"])

    # 2. orcamento_itens
    op.create_table(
        "orcamento_itens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("orcamento_id", sa.Integer(), nullable=False),
        sa.Column("produto_cliente_id", sa.Integer(), nullable=False),
        sa.Column("codigo_produto", sa.String(50), nullable=True),
        sa.Column("descricao_produto", sa.String(255), nullable=True),
        sa.Column("quantidade", sa.Numeric(15, 3), nullable=False),
        sa.Column("preco_unitario", sa.Numeric(15, 2), nullable=False),
        sa.Column("desconto_percentual", sa.Numeric(5, 2), nullable=True),
        sa.Column("desconto_valor", sa.Numeric(15, 2), nullable=True),
        sa.Column("total_item", sa.Numeric(15, 2), nullable=False),
        sa.Column("observacao_item", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["orcamento_id"], ["orcamentos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["produto_cliente_id"], ["produtos_cliente.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_orcamento_itens_orcamento_id", "orcamento_itens", ["orcamento_id"])
    op.create_index("ix_orcamento_itens_produto_cliente_id", "orcamento_itens", ["produto_cliente_id"])

    # 3. pedidos
    op.create_table(
        "pedidos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("orcamento_id", sa.Integer(), nullable=True),
        sa.Column("venda_id", sa.Integer(), nullable=True, comment="Quando pedido nasce de venda no PDV"),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("vendedor_id", sa.Integer(), nullable=True),
        sa.Column("numero_pedido", sa.String(50), nullable=False),
        sa.Column("data_pedido", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("data_prevista_entrega", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="rascunho"),
        sa.Column("reserva_estoque", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("data_reserva", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subtotal", sa.Numeric(15, 2), nullable=True),
        sa.Column("desconto", sa.Numeric(15, 2), nullable=True),
        sa.Column("acrescimo", sa.Numeric(15, 2), nullable=True),
        sa.Column("total", sa.Numeric(15, 2), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["orcamento_id"], ["orcamentos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["venda_id"], ["vendas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vendedor_id"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_pedidos_cliente_id", "pedidos", ["cliente_id"])
    op.create_index("ix_pedidos_status", "pedidos", ["status"])
    op.create_index("ix_pedidos_data_pedido", "pedidos", ["data_pedido"])
    op.create_index("ix_pedidos_orcamento_id", "pedidos", ["orcamento_id"])
    op.create_index("ix_pedidos_venda_id", "pedidos", ["venda_id"])
    op.create_unique_constraint("uq_pedidos_cliente_numero", "pedidos", ["cliente_id", "numero_pedido"])

    # 4. orcamentos.convertido_em_pedido_id (FK para pedidos)
    op.add_column("orcamentos", sa.Column("convertido_em_pedido_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_orcamentos_convertido_em_pedido_id", "orcamentos", "pedidos", ["convertido_em_pedido_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_orcamentos_convertido_em_pedido_id", "orcamentos", ["convertido_em_pedido_id"])

    # 5. pedido_itens
    op.create_table(
        "pedido_itens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("produto_cliente_id", sa.Integer(), nullable=False),
        sa.Column("codigo_produto", sa.String(50), nullable=True),
        sa.Column("descricao_produto", sa.String(255), nullable=True),
        sa.Column("quantidade", sa.Numeric(15, 3), nullable=False),
        sa.Column("quantidade_faturada", sa.Numeric(15, 3), nullable=False, server_default="0"),
        sa.Column("preco_unitario", sa.Numeric(15, 2), nullable=False),
        sa.Column("desconto_percentual", sa.Numeric(5, 2), nullable=True),
        sa.Column("desconto_valor", sa.Numeric(15, 2), nullable=True),
        sa.Column("total_item", sa.Numeric(15, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["produto_cliente_id"], ["produtos_cliente.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_pedido_itens_pedido_id", "pedido_itens", ["pedido_id"])
    op.create_index("ix_pedido_itens_produto_cliente_id", "pedido_itens", ["produto_cliente_id"])

    # 6. pedido_faturamento
    op.create_table(
        "pedido_faturamento",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("nota_fiscal_id", sa.Integer(), nullable=False),
        sa.Column("data_faturamento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valor_faturado", sa.Numeric(15, 2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["nota_fiscal_id"], ["notas_fiscais.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_pedido_faturamento_pedido_id", "pedido_faturamento", ["pedido_id"])
    op.create_index("ix_pedido_faturamento_nota_fiscal_id", "pedido_faturamento", ["nota_fiscal_id"])

    # 7. pedido_historico
    op.create_table(
        "pedido_historico",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("status_anterior", sa.String(50), nullable=True),
        sa.Column("status_novo", sa.String(50), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("data_mudanca", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_pedido_historico_pedido_id", "pedido_historico", ["pedido_id"])

    # 8. reserva_estoque
    op.create_table(
        "reserva_estoque",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("produto_cliente_id", sa.Integer(), nullable=False),
        sa.Column("quantidade_reservada", sa.Numeric(15, 3), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["produto_cliente_id"], ["produtos_cliente.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_reserva_estoque_pedido_id", "reserva_estoque", ["pedido_id"])
    op.create_index("ix_reserva_estoque_produto_cliente_id", "reserva_estoque", ["produto_cliente_id"])

    # 9. notas_fiscais.pedido_id
    op.add_column("notas_fiscais", sa.Column("pedido_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_notas_fiscais_pedido_id", "notas_fiscais", "pedidos", ["pedido_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_notas_fiscais_pedido_id", "notas_fiscais", ["pedido_id"])


def downgrade() -> None:
    op.drop_index("ix_notas_fiscais_pedido_id", table_name="notas_fiscais")
    op.drop_constraint("fk_notas_fiscais_pedido_id", "notas_fiscais", type_="foreignkey")
    op.drop_column("notas_fiscais", "pedido_id")

    op.drop_index("ix_reserva_estoque_produto_cliente_id", table_name="reserva_estoque")
    op.drop_index("ix_reserva_estoque_pedido_id", table_name="reserva_estoque")
    op.drop_table("reserva_estoque")

    op.drop_index("ix_pedido_historico_pedido_id", table_name="pedido_historico")
    op.drop_table("pedido_historico")

    op.drop_index("ix_pedido_faturamento_nota_fiscal_id", table_name="pedido_faturamento")
    op.drop_index("ix_pedido_faturamento_pedido_id", table_name="pedido_faturamento")
    op.drop_table("pedido_faturamento")

    op.drop_index("ix_pedido_itens_produto_cliente_id", table_name="pedido_itens")
    op.drop_index("ix_pedido_itens_pedido_id", table_name="pedido_itens")
    op.drop_table("pedido_itens")

    op.drop_index("ix_orcamentos_convertido_em_pedido_id", table_name="orcamentos")
    op.drop_constraint("fk_orcamentos_convertido_em_pedido_id", "orcamentos", type_="foreignkey")
    op.drop_column("orcamentos", "convertido_em_pedido_id")

    op.drop_constraint("uq_pedidos_cliente_numero", "pedidos", type_="unique")
    op.drop_index("ix_pedidos_venda_id", table_name="pedidos")
    op.drop_index("ix_pedidos_orcamento_id", table_name="pedidos")
    op.drop_index("ix_pedidos_data_pedido", table_name="pedidos")
    op.drop_index("ix_pedidos_status", table_name="pedidos")
    op.drop_index("ix_pedidos_cliente_id", table_name="pedidos")
    op.drop_table("pedidos")

    op.drop_index("ix_orcamento_itens_produto_cliente_id", table_name="orcamento_itens")
    op.drop_index("ix_orcamento_itens_orcamento_id", table_name="orcamento_itens")
    op.drop_table("orcamento_itens")

    op.drop_constraint("uq_orcamentos_cliente_numero", "orcamentos", type_="unique")
    op.drop_index("ix_orcamentos_data_validade", table_name="orcamentos")
    op.drop_index("ix_orcamentos_status", table_name="orcamentos")
    op.drop_index("ix_orcamentos_cliente_id", table_name="orcamentos")
    op.drop_table("orcamentos")
