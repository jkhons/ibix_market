"""Produtos e estoque por estabelecimento (Fase 2 - Plano PDV Hierarquia).

Revision ID: dd33ff469v9
Revises: cc22ee469u8
Create Date: 2026-02-18

- produtos_cliente: catálogo por estabelecimento (cliente_id), UNIQUE(cliente_id, codigo).
- codigos_barras_cliente: múltiplos códigos de barras por produto_cliente.
- fornecedores_cliente: fornecedores por estabelecimento.
- produtos_fornecedor: vínculo produto-fornecedor com código e preço.
- movimentacoes_estoque: entradas/saídas/ajustes por produto_cliente.
- venda_itens.produto_cliente_id (nullable) para vendas por estabelecimento.
"""
import sqlalchemy as sa
from alembic import op

revision = "dd33ff469v9"
down_revision = "cc22ee469u8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # produtos_cliente: produto por estabelecimento (loja)
    op.create_table(
        "produtos_cliente",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False, comment="Estabelecimento (clientes.id)"),
        sa.Column("codigo", sa.String(50), nullable=False, comment="Código/SKU único por estabelecimento"),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ncm", sa.String(10), nullable=True),
        sa.Column("unidade_medida", sa.String(20), nullable=False, server_default="UN"),
        sa.Column("valor_custo", sa.Numeric(10, 2), nullable=True),
        sa.Column("valor_venda", sa.Numeric(10, 2), nullable=True),
        sa.Column("quantidade_atual", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("quantidade_minima", sa.Numeric(10, 2), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("cliente_id", "codigo", name="uq_produtos_cliente_cliente_codigo"),
    )
    op.create_index("ix_produtos_cliente_cliente_id", "produtos_cliente", ["cliente_id"])

    # codigos_barras_cliente: múltiplos códigos de barras por produto
    op.create_table(
        "codigos_barras_cliente",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("produto_cliente_id", sa.Integer(), nullable=False),
        sa.Column("codigo_barras", sa.String(50), nullable=False),
        sa.Column("principal", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["produto_cliente_id"], ["produtos_cliente.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("codigo_barras", name="uq_codigos_barras_cliente_codigo"),
    )
    op.create_index("ix_codigos_barras_cliente_produto_cliente_id", "codigos_barras_cliente", ["produto_cliente_id"])

    # fornecedores_cliente: fornecedores por estabelecimento
    op.create_table(
        "fornecedores_cliente",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("cnpj", sa.String(18), nullable=True),
        sa.Column("contato", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telefone", sa.String(50), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_fornecedores_cliente_cliente_id", "fornecedores_cliente", ["cliente_id"])

    # produtos_fornecedor: vínculo produto-fornecedor (código no fornecedor, preço compra)
    op.create_table(
        "produtos_fornecedor",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("produto_cliente_id", sa.Integer(), nullable=False),
        sa.Column("fornecedor_cliente_id", sa.Integer(), nullable=False),
        sa.Column("codigo_fornecedor", sa.String(50), nullable=True),
        sa.Column("preco_compra", sa.Numeric(10, 2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["produto_cliente_id"], ["produtos_cliente.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fornecedor_cliente_id"], ["fornecedores_cliente.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_produtos_fornecedor_produto_cliente_id", "produtos_fornecedor", ["produto_cliente_id"])
    op.create_index("ix_produtos_fornecedor_fornecedor_cliente_id", "produtos_fornecedor", ["fornecedor_cliente_id"])

    # movimentacoes_estoque: histórico por produto_cliente
    op.create_table(
        "movimentacoes_estoque",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("produto_cliente_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False, comment="entrada, saida, ajuste, transferencia"),
        sa.Column("quantidade", sa.Numeric(10, 2), nullable=False),
        sa.Column("valor_unitario", sa.Numeric(10, 2), nullable=True),
        sa.Column("documento_ref", sa.String(100), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["produto_cliente_id"], ["produtos_cliente.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_movimentacoes_estoque_produto_cliente_id", "movimentacoes_estoque", ["produto_cliente_id"])

    # venda_itens: estoque_id passa a ser nullable (itens podem usar produto_cliente_id); produto_cliente_id adicionado
    op.alter_column(
        "venda_itens",
        "estoque_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.add_column(
        "venda_itens",
        sa.Column("produto_cliente_id", sa.Integer(), nullable=True, comment="Produto do estabelecimento (Fase 2); alternativa a estoque_id"),
    )
    op.create_foreign_key(
        "fk_venda_itens_produto_cliente_id",
        "venda_itens",
        "produtos_cliente",
        ["produto_cliente_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_venda_itens_produto_cliente_id", "venda_itens", ["produto_cliente_id"])


def downgrade() -> None:
    op.drop_index("ix_venda_itens_produto_cliente_id", table_name="venda_itens")
    op.drop_constraint("fk_venda_itens_produto_cliente_id", "venda_itens", type_="foreignkey")
    op.drop_column("venda_itens", "produto_cliente_id")
    op.alter_column(
        "venda_itens",
        "estoque_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_index("ix_movimentacoes_estoque_produto_cliente_id", table_name="movimentacoes_estoque")
    op.drop_table("movimentacoes_estoque")

    op.drop_index("ix_produtos_fornecedor_fornecedor_cliente_id", table_name="produtos_fornecedor")
    op.drop_index("ix_produtos_fornecedor_produto_cliente_id", table_name="produtos_fornecedor")
    op.drop_table("produtos_fornecedor")

    op.drop_index("ix_fornecedores_cliente_cliente_id", table_name="fornecedores_cliente")
    op.drop_table("fornecedores_cliente")

    op.drop_index("ix_codigos_barras_cliente_produto_cliente_id", table_name="codigos_barras_cliente")
    op.drop_table("codigos_barras_cliente")

    op.drop_index("ix_produtos_cliente_cliente_id", table_name="produtos_cliente")
    op.drop_table("produtos_cliente")
