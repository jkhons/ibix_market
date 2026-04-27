"""Marketplace: tabelas lojas_marketplace, categorias_plataforma, anuncios_plataforma, sync_controle, consumidores_marketplace, enderecos_consumidor, pedidos_marketplace, pedido_itens_marketplace, avaliacoes_marketplace, extrato_loja.

Revision ID: mk01_tables
Revises: os02_perm
Create Date: 2026-03-07

Ordem de criação respeitando FKs. Sem dados mockados.
"""
import sqlalchemy as sa
from alembic import op

revision = "mk01_tables"
down_revision = "os02_perm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. lojas_marketplace (depende de clientes)
    op.create_table(
        "lojas_marketplace",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("slug", sa.String(100), nullable=True),
        sa.Column("nome_loja", sa.String(200), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("banner_url", sa.Text(), nullable=True),
        sa.Column("tipo_entrega", sa.String(20), nullable=False, server_default="retirada"),
        sa.Column("raio_entrega_km", sa.Integer(), nullable=True),
        sa.Column("taxa_entrega_fixa", sa.Numeric(10, 2), nullable=True),
        sa.Column("entrega_gratis_apos", sa.Numeric(10, 2), nullable=True),
        sa.Column("avaliacao_media", sa.Numeric(3, 2), nullable=False, server_default="0"),
        sa.Column("total_vendas_marketplace", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("faturamento_total", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_lojas_marketplace_cliente_id", "lojas_marketplace", ["cliente_id"], unique=True)
    op.create_index("ix_lojas_marketplace_slug", "lojas_marketplace", ["slug"], unique=True)

    # 2. categorias_plataforma (auto-referência opcional)
    op.create_table(
        "categorias_plataforma",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("icone", sa.String(50), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=True),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("categoria_pai_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["categoria_pai_id"], ["categorias_plataforma.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_categorias_plataforma_slug", "categorias_plataforma", ["slug"], unique=True)

    # 3. consumidores_marketplace
    op.create_table(
        "consumidores_marketplace",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("documento", sa.String(20), nullable=True),
        sa.Column("aceite_termos", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consumidores_marketplace_email", "consumidores_marketplace", ["email"], unique=True)

    # 4. enderecos_consumidor
    op.create_table(
        "enderecos_consumidor",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("consumidor_id", sa.Integer(), nullable=False),
        sa.Column("apelido", sa.String(50), nullable=True),
        sa.Column("cep", sa.String(20), nullable=True),
        sa.Column("logradouro", sa.String(255), nullable=True),
        sa.Column("numero", sa.String(20), nullable=True),
        sa.Column("complemento", sa.String(100), nullable=True),
        sa.Column("bairro", sa.String(100), nullable=True),
        sa.Column("cidade", sa.String(100), nullable=True),
        sa.Column("uf", sa.String(2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["consumidor_id"], ["consumidores_marketplace.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_enderecos_consumidor_consumidor_id", "enderecos_consumidor", ["consumidor_id"])

    # 5. anuncios_plataforma (depende de lojas_marketplace, produtos_cliente, categorias_plataforma)
    op.create_table(
        "anuncios_plataforma",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("loja_id", sa.Integer(), nullable=False),
        sa.Column("produto_ca_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="rascunho"),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("imagens", sa.Text(), nullable=True),
        sa.Column("preco_original", sa.Numeric(10, 2), nullable=False),
        sa.Column("preco_promocional", sa.Numeric(10, 2), nullable=True),
        sa.Column("tipo_estoque", sa.String(20), nullable=False, server_default="sincronizado"),
        sa.Column("estoque_atual", sa.Numeric(10, 2), nullable=True),
        sa.Column("estoque_minimo_alerta", sa.Integer(), nullable=True, server_default="5"),
        sa.Column("variacoes", sa.Text(), nullable=True),
        sa.Column("atributos", sa.Text(), nullable=True),
        sa.Column("visualizacoes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cliques", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vendas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ultima_sincronizacao", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["loja_id"], ["lojas_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["produto_ca_id"], ["produtos_cliente.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["categoria_id"], ["categorias_plataforma.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("loja_id", "produto_ca_id", name="uq_anuncios_plataforma_loja_produto"),
    )
    op.create_index("ix_anuncios_plataforma_loja_id", "anuncios_plataforma", ["loja_id"])
    op.create_index("ix_anuncios_plataforma_produto_ca_id", "anuncios_plataforma", ["produto_ca_id"])
    op.create_index("ix_anuncios_plataforma_categoria_id", "anuncios_plataforma", ["categoria_id"])
    op.create_index("ix_anuncios_plataforma_status", "anuncios_plataforma", ["status"])

    # 6. sync_controle
    op.create_table(
        "sync_controle",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("loja_id", sa.Integer(), nullable=False),
        sa.Column("tipo_sync", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("dados_resumo", sa.Text(), nullable=True),
        sa.Column("log_erros", sa.Text(), nullable=True),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["loja_id"], ["lojas_marketplace.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sync_controle_loja_id", "sync_controle", ["loja_id"])

    # 7. pedidos_marketplace
    op.create_table(
        "pedidos_marketplace",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("loja_id", sa.Integer(), nullable=False),
        sa.Column("comprador_id", sa.Integer(), nullable=True),
        sa.Column("comprador_nome", sa.String(200), nullable=False),
        sa.Column("comprador_email", sa.String(255), nullable=True),
        sa.Column("comprador_telefone", sa.String(20), nullable=True),
        sa.Column("comprador_documento", sa.String(20), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("desconto", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("taxa_entrega", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("comissao_plataforma", sa.Numeric(10, 2), nullable=True),
        sa.Column("percentual_comissao", sa.Numeric(5, 2), nullable=True),
        sa.Column("valor_liquido_loja", sa.Numeric(10, 2), nullable=True),
        sa.Column("status_pedido", sa.String(30), nullable=False, server_default="aguardando_pagamento"),
        sa.Column("status_pagamento", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("endereco_entrega", sa.Text(), nullable=True),
        sa.Column("tipo_entrega", sa.String(20), nullable=False),
        sa.Column("gateway_pagamento", sa.String(50), nullable=True),
        sa.Column("transaction_id", sa.String(200), nullable=True),
        sa.Column("split_info", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["loja_id"], ["lojas_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comprador_id"], ["consumidores_marketplace.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_pedidos_marketplace_loja_id", "pedidos_marketplace", ["loja_id"])
    op.create_index("ix_pedidos_marketplace_comprador_id", "pedidos_marketplace", ["comprador_id"])
    op.create_index("ix_pedidos_marketplace_status_pedido", "pedidos_marketplace", ["status_pedido"])
    op.create_index("ix_pedidos_marketplace_created_at", "pedidos_marketplace", ["created_at"])

    # 8. pedido_itens_marketplace
    op.create_table(
        "pedido_itens_marketplace",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("anuncio_id", sa.Integer(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("preco_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("preco_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("variacao_selecionada", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["anuncio_id"], ["anuncios_plataforma.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_pedido_itens_marketplace_pedido_id", "pedido_itens_marketplace", ["pedido_id"])
    op.create_index("ix_pedido_itens_marketplace_anuncio_id", "pedido_itens_marketplace", ["anuncio_id"])

    # 9. avaliacoes_marketplace
    op.create_table(
        "avaliacoes_marketplace",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("anuncio_id", sa.Integer(), nullable=False),
        sa.Column("loja_id", sa.Integer(), nullable=False),
        sa.Column("comprador_nome", sa.String(200), nullable=True),
        sa.Column("nota", sa.Integer(), nullable=False),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("resposta_loja", sa.Text(), nullable=True),
        sa.Column("imagens", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["anuncio_id"], ["anuncios_plataforma.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["loja_id"], ["lojas_marketplace.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_avaliacoes_marketplace_pedido_id", "avaliacoes_marketplace", ["pedido_id"])
    op.create_index("ix_avaliacoes_marketplace_anuncio_id", "avaliacoes_marketplace", ["anuncio_id"])
    op.create_index("ix_avaliacoes_marketplace_loja_id", "avaliacoes_marketplace", ["loja_id"])

    # 10. extrato_loja
    op.create_table(
        "extrato_loja",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("loja_id", sa.Integer(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("valor_bruto", sa.Numeric(10, 2), nullable=True),
        sa.Column("valor_taxa", sa.Numeric(10, 2), nullable=True),
        sa.Column("valor_liquido", sa.Numeric(10, 2), nullable=True),
        sa.Column("saldo_anterior", sa.Numeric(10, 2), nullable=True),
        sa.Column("saldo_atual", sa.Numeric(10, 2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendente"),
        sa.Column("data_disponivel", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_pagamento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comprovante", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["loja_id"], ["lojas_marketplace.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos_marketplace.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_extrato_loja_loja_id", "extrato_loja", ["loja_id"])
    op.create_index("ix_extrato_loja_pedido_id", "extrato_loja", ["pedido_id"])

    # Índice full-text para busca em anuncios_plataforma (PostgreSQL)
    op.execute(
        "CREATE INDEX ix_anuncios_plataforma_busca ON anuncios_plataforma "
        "USING GIN(to_tsvector('portuguese', titulo || ' ' || COALESCE(descricao, '')))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_anuncios_plataforma_busca")
    op.drop_index("ix_extrato_loja_pedido_id", table_name="extrato_loja")
    op.drop_index("ix_extrato_loja_loja_id", table_name="extrato_loja")
    op.drop_table("extrato_loja")
    op.drop_index("ix_avaliacoes_marketplace_loja_id", table_name="avaliacoes_marketplace")
    op.drop_index("ix_avaliacoes_marketplace_anuncio_id", table_name="avaliacoes_marketplace")
    op.drop_index("ix_avaliacoes_marketplace_pedido_id", table_name="avaliacoes_marketplace")
    op.drop_table("avaliacoes_marketplace")
    op.drop_index("ix_pedido_itens_marketplace_anuncio_id", table_name="pedido_itens_marketplace")
    op.drop_index("ix_pedido_itens_marketplace_pedido_id", table_name="pedido_itens_marketplace")
    op.drop_table("pedido_itens_marketplace")
    op.drop_index("ix_pedidos_marketplace_created_at", table_name="pedidos_marketplace")
    op.drop_index("ix_pedidos_marketplace_status_pedido", table_name="pedidos_marketplace")
    op.drop_index("ix_pedidos_marketplace_comprador_id", table_name="pedidos_marketplace")
    op.drop_index("ix_pedidos_marketplace_loja_id", table_name="pedidos_marketplace")
    op.drop_table("pedidos_marketplace")
    op.drop_index("ix_sync_controle_loja_id", table_name="sync_controle")
    op.drop_table("sync_controle")
    op.drop_index("ix_anuncios_plataforma_status", table_name="anuncios_plataforma")
    op.drop_index("ix_anuncios_plataforma_categoria_id", table_name="anuncios_plataforma")
    op.drop_index("ix_anuncios_plataforma_produto_ca_id", table_name="anuncios_plataforma")
    op.drop_index("ix_anuncios_plataforma_loja_id", table_name="anuncios_plataforma")
    op.drop_table("anuncios_plataforma")
    op.drop_index("ix_enderecos_consumidor_consumidor_id", table_name="enderecos_consumidor")
    op.drop_table("enderecos_consumidor")
    op.drop_index("ix_consumidores_marketplace_email", table_name="consumidores_marketplace")
    op.drop_table("consumidores_marketplace")
    op.drop_index("ix_categorias_plataforma_slug", table_name="categorias_plataforma")
    op.drop_table("categorias_plataforma")
    op.drop_index("ix_lojas_marketplace_slug", table_name="lojas_marketplace")
    op.drop_index("ix_lojas_marketplace_cliente_id", table_name="lojas_marketplace")
    op.drop_table("lojas_marketplace")
