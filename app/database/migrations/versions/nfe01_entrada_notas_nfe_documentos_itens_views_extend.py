"""Módulo Entrada de Notas NFe: nfe_documentos, nfe_itens, views, estender produtos_fornecedor e movimentacoes_estoque.

Revision ID: nfe01_entrada
Revises: cep20_v20
Create Date: 2026-03-02

- nfe_documentos: cabeçalho da NF-e importada (entrada), escopo cliente_id.
- nfe_itens: itens do XML + conciliação (produto_cliente_id, conciliar_status).
- vw_nfe_itens_pendentes_conciliacao, vw_nfe_itens_conciliacao (PostgreSQL).
- produtos_fornecedor: xprod_amostra, ean_amostra, ucom_amostra, fator_conversao, ativo; UNIQUE(fornecedor_cliente_id, codigo_fornecedor).
- movimentacoes_estoque: nfe_documento_id, nfe_item_id, custo_total.
"""
import sqlalchemy as sa
from alembic import op

revision = "nfe01_entrada"
down_revision = "cep20_v20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    is_pg = conn.dialect.name == "postgresql"

    # ========== 1) nfe_documentos ==========
    op.create_table(
        "nfe_documentos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False, comment="Estabelecimento que importa/recebe a nota"),
        sa.Column("chave_acesso_44", sa.String(44), nullable=False),
        sa.Column("modelo", sa.String(5), nullable=True),
        sa.Column("serie", sa.String(10), nullable=True),
        sa.Column("numero", sa.String(20), nullable=True),
        sa.Column("emissao_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entrada_saida", sa.String(20), nullable=False),
        sa.Column("ambiente", sa.String(20), nullable=True),
        sa.Column("emitente_fornecedor_id", sa.Integer(), nullable=True),
        sa.Column("total_produtos", sa.Numeric(18, 2), nullable=True),
        sa.Column("total_nota", sa.Numeric(18, 2), nullable=True),
        sa.Column("xml_original", sa.Text(), nullable=True),
        sa.Column("xml_sha256", sa.String(64), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="IMPORTADO"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["emitente_fornecedor_id"], ["fornecedores_cliente.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_nfe_documentos_cliente_id", "nfe_documentos", ["cliente_id"])
    op.create_index("ix_nfe_documentos_emissao_em", "nfe_documentos", ["emissao_em"])
    op.create_index("ix_nfe_documentos_entrada_saida", "nfe_documentos", ["entrada_saida"])
    op.create_index("ix_nfe_documentos_emitente_fornecedor_id", "nfe_documentos", ["emitente_fornecedor_id"])
    op.create_index("uq_nfe_documentos_chave_acesso_44", "nfe_documentos", ["chave_acesso_44"], unique=True)

    # ========== 2) nfe_itens ==========
    op.create_table(
        "nfe_itens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("nfe_id", sa.Integer(), nullable=False),
        sa.Column("numero_item", sa.Integer(), nullable=True),
        sa.Column("cprod_xml", sa.String(60), nullable=True),
        sa.Column("xprod_xml", sa.Text(), nullable=True),
        sa.Column("ean_xml", sa.String(14), nullable=True),
        sa.Column("ncm_xml", sa.String(10), nullable=True),
        sa.Column("cfop_xml", sa.String(10), nullable=True),
        sa.Column("ucom_xml", sa.String(10), nullable=True),
        sa.Column("qcom_xml", sa.Numeric(18, 6), nullable=True),
        sa.Column("vuncom_xml", sa.Numeric(18, 6), nullable=True),
        sa.Column("vprod_xml", sa.Numeric(18, 2), nullable=True),
        sa.Column("vdesc_xml", sa.Numeric(18, 2), nullable=True),
        sa.Column("vfrete_xml", sa.Numeric(18, 2), nullable=True),
        sa.Column("vseg_xml", sa.Numeric(18, 2), nullable=True),
        sa.Column("voutro_xml", sa.Numeric(18, 2), nullable=True),
        sa.Column("vipi_xml", sa.Numeric(18, 2), nullable=True),
        sa.Column("vicmsst_xml", sa.Numeric(18, 2), nullable=True),
        sa.Column("produto_cliente_id", sa.Integer(), nullable=True),
        sa.Column("fornecedor_id", sa.Integer(), nullable=True),
        sa.Column("conciliar_status", sa.String(20), nullable=False, server_default="PENDENTE"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["nfe_id"], ["nfe_documentos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["produto_cliente_id"], ["produtos_cliente.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fornecedor_id"], ["fornecedores_cliente.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_nfe_itens_nfe_id", "nfe_itens", ["nfe_id"])
    op.create_index("ix_nfe_itens_produto_cliente_id", "nfe_itens", ["produto_cliente_id"])
    op.create_index("ix_nfe_itens_fornecedor_cprod", "nfe_itens", ["fornecedor_id", "cprod_xml"])

    # ========== 3) Estender produtos_fornecedor (antes das views que usam m.ativo) ==========
    op.add_column("produtos_fornecedor", sa.Column("xprod_amostra", sa.String(500), nullable=True))
    op.add_column("produtos_fornecedor", sa.Column("ean_amostra", sa.String(14), nullable=True))
    op.add_column("produtos_fornecedor", sa.Column("ucom_amostra", sa.String(10), nullable=True))
    op.add_column("produtos_fornecedor", sa.Column("fator_conversao", sa.Numeric(18, 6), nullable=False, server_default="1"))
    op.add_column("produtos_fornecedor", sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()))
    if is_pg:
        op.execute("""
        DELETE FROM produtos_fornecedor a
        USING produtos_fornecedor b
        WHERE a.fornecedor_cliente_id = b.fornecedor_cliente_id
          AND (a.codigo_fornecedor = b.codigo_fornecedor OR (a.codigo_fornecedor IS NULL AND b.codigo_fornecedor IS NULL))
          AND a.id > b.id
        """)
    op.create_unique_constraint(
        "uq_produtos_fornecedor_fornecedor_codigo",
        "produtos_fornecedor",
        ["fornecedor_cliente_id", "codigo_fornecedor"],
    )

    # ========== 4) Views (PostgreSQL) ==========
    if is_pg:
        op.execute("""
        CREATE OR REPLACE VIEW vw_nfe_itens_pendentes_conciliacao AS
        SELECT
          nd.cliente_id      AS cliente_id,
          nd.id              AS nfe_id,
          nd.chave_acesso_44,
          nd.modelo,
          nd.serie,
          nd.numero,
          nd.emissao_em,
          nd.entrada_saida,
          nd.ambiente,
          nd.status          AS nfe_status,
          f.id               AS fornecedor_id,
          f.cnpj             AS fornecedor_cnpj,
          f.nome             AS fornecedor_nome,
          ni.id              AS nfe_item_id,
          ni.numero_item,
          ni.cprod_xml,
          ni.xprod_xml,
          ni.ean_xml,
          ni.ncm_xml,
          ni.cfop_xml,
          ni.ucom_xml,
          ni.qcom_xml,
          ni.vuncom_xml,
          ni.vprod_xml,
          ni.vdesc_xml,
          ni.vfrete_xml,
          ni.vseg_xml,
          ni.voutro_xml,
          ni.vipi_xml,
          ni.vicmsst_xml,
          ni.conciliar_status,
          ni.produto_cliente_id,
          p.codigo           AS produto_codigo_interno,
          p.nome             AS produto_nome_padrao,
          p.unidade_medida   AS produto_unidade_base
        FROM nfe_itens ni
        JOIN nfe_documentos nd ON nd.id = ni.nfe_id
        LEFT JOIN fornecedores_cliente f ON f.id = COALESCE(ni.fornecedor_id, nd.emitente_fornecedor_id)
        LEFT JOIN produtos_cliente p ON p.id = ni.produto_cliente_id
        WHERE nd.entrada_saida = 'ENTRADA'
          AND ni.conciliar_status = 'PENDENTE'
        """)
        op.execute("""
        CREATE OR REPLACE VIEW vw_nfe_itens_conciliacao AS
        SELECT
          nd.cliente_id      AS cliente_id,
          nd.id              AS nfe_id,
          nd.chave_acesso_44,
          nd.emissao_em,
          nd.numero,
          nd.serie,
          nd.status          AS nfe_status,
          f.id               AS fornecedor_id,
          f.cnpj             AS fornecedor_cnpj,
          f.nome             AS fornecedor_nome,
          ni.id              AS nfe_item_id,
          ni.numero_item,
          ni.cprod_xml,
          ni.xprod_xml,
          ni.ucom_xml,
          ni.qcom_xml,
          ni.vuncom_xml,
          ni.vprod_xml,
          ni.vdesc_xml,
          ni.vfrete_xml,
          ni.vseg_xml,
          ni.voutro_xml,
          ni.vipi_xml,
          ni.vicmsst_xml,
          ni.conciliar_status,
          ni.produto_cliente_id,
          p.codigo           AS produto_codigo_interno,
          p.nome             AS produto_nome_padrao,
          m.id               AS map_id,
          m.produto_cliente_id AS map_produto_id,
          mp.codigo          AS map_produto_codigo,
          mp.nome            AS map_produto_nome,
          m.fator_conversao
        FROM nfe_itens ni
        JOIN nfe_documentos nd ON nd.id = ni.nfe_id
        LEFT JOIN fornecedores_cliente f ON f.id = COALESCE(ni.fornecedor_id, nd.emitente_fornecedor_id)
        LEFT JOIN produtos_cliente p ON p.id = ni.produto_cliente_id
        LEFT JOIN produtos_fornecedor m
          ON m.fornecedor_cliente_id = nd.emitente_fornecedor_id
         AND m.codigo_fornecedor = ni.cprod_xml
         AND (m.ativo IS NULL OR m.ativo = TRUE)
        LEFT JOIN produtos_cliente mp ON mp.id = m.produto_cliente_id
        WHERE nd.entrada_saida = 'ENTRADA'
        """)

    # ========== 5) Estender movimentacoes_estoque ==========
    op.add_column("movimentacoes_estoque", sa.Column("nfe_documento_id", sa.Integer(), nullable=True))
    op.add_column("movimentacoes_estoque", sa.Column("nfe_item_id", sa.Integer(), nullable=True))
    op.add_column("movimentacoes_estoque", sa.Column("custo_total", sa.Numeric(18, 2), nullable=True))
    op.create_foreign_key(
        "fk_movimentacoes_estoque_nfe_documento",
        "movimentacoes_estoque",
        "nfe_documentos",
        ["nfe_documento_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_movimentacoes_estoque_nfe_item",
        "movimentacoes_estoque",
        "nfe_itens",
        ["nfe_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_movimentacoes_estoque_nfe_documento_id", "movimentacoes_estoque", ["nfe_documento_id"])
    op.create_index("ix_movimentacoes_estoque_nfe_item_id", "movimentacoes_estoque", ["nfe_item_id"])


def downgrade() -> None:
    conn = op.get_bind()
    is_pg = conn.dialect.name == "postgresql"

    # 5) Reverter movimentacoes_estoque
    op.drop_index("ix_movimentacoes_estoque_nfe_item_id", table_name="movimentacoes_estoque")
    op.drop_index("ix_movimentacoes_estoque_nfe_documento_id", table_name="movimentacoes_estoque")
    op.drop_constraint("fk_movimentacoes_estoque_nfe_item", "movimentacoes_estoque", type_="foreignkey")
    op.drop_constraint("fk_movimentacoes_estoque_nfe_documento", "movimentacoes_estoque", type_="foreignkey")
    op.drop_column("movimentacoes_estoque", "custo_total")
    op.drop_column("movimentacoes_estoque", "nfe_item_id")
    op.drop_column("movimentacoes_estoque", "nfe_documento_id")

    # 4) Reverter produtos_fornecedor
    op.drop_constraint("uq_produtos_fornecedor_fornecedor_codigo", "produtos_fornecedor", type_="unique")
    op.drop_column("produtos_fornecedor", "ativo")
    op.drop_column("produtos_fornecedor", "fator_conversao")
    op.drop_column("produtos_fornecedor", "ucom_amostra")
    op.drop_column("produtos_fornecedor", "ean_amostra")
    op.drop_column("produtos_fornecedor", "xprod_amostra")

    # 3) Views
    if is_pg:
        op.execute("DROP VIEW IF EXISTS vw_nfe_itens_conciliacao")
        op.execute("DROP VIEW IF EXISTS vw_nfe_itens_pendentes_conciliacao")

    # 2) nfe_itens
    op.drop_index("ix_nfe_itens_fornecedor_cprod", table_name="nfe_itens")
    op.drop_index("ix_nfe_itens_produto_cliente_id", table_name="nfe_itens")
    op.drop_index("ix_nfe_itens_nfe_id", table_name="nfe_itens")
    op.drop_table("nfe_itens")

    # 1) nfe_documentos
    op.drop_index("uq_nfe_documentos_chave_acesso_44", table_name="nfe_documentos")
    op.drop_index("ix_nfe_documentos_emitente_fornecedor_id", table_name="nfe_documentos")
    op.drop_index("ix_nfe_documentos_entrada_saida", table_name="nfe_documentos")
    op.drop_index("ix_nfe_documentos_emissao_em", table_name="nfe_documentos")
    op.drop_index("ix_nfe_documentos_cliente_id", table_name="nfe_documentos")
    op.drop_table("nfe_documentos")
