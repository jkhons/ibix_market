"""Bloco A — Mapa Fiscal: tabelas fiscal_documentos, snapshots, itens, totais, transporte, duplicatas, xml_store, eventos.

Revision ID: fiscal_doc_mapa
Revises: fiscal_baixar_xml_ca
Create Date: 2026-03-12

Conforme plano NF-e: estrutura de documentos fiscais com snapshots imutáveis,
numeração por tenant_id + empresa_emitente_id + modelo + serie.
NÃO duplica notas_fiscais: é modelo novo para evolução futura.
"""
import sqlalchemy as sa
from alembic import op

revision = "fiscal_doc_mapa"
down_revision = "fiscal_baixar_xml_ca"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. fiscal_documentos (cabeçalho)
    op.create_table(
        "fiscal_documentos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("cliente_administrador_id", sa.BigInteger(), nullable=False),
        sa.Column("empresa_emitente_id", sa.BigInteger(), nullable=False),
        sa.Column("pedido_id", sa.BigInteger(), nullable=True),
        sa.Column("tipo_documento", sa.String(20), nullable=False, server_default="NFE"),
        sa.Column("modelo", sa.String(2), nullable=False, server_default="55"),
        sa.Column("serie", sa.String(3), nullable=False),
        sa.Column("numero", sa.BigInteger(), nullable=False),
        sa.Column("natureza_operacao", sa.String(120), nullable=False),
        sa.Column("finalidade_emissao", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("tipo_operacao", sa.SmallInteger(), nullable=False),
        sa.Column("forma_pagamento", sa.String(2), nullable=True),
        sa.Column("presenca_comprador", sa.String(2), nullable=True),
        sa.Column("ambiente", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="rascunho"),
        sa.Column("chave_acesso", sa.String(44), nullable=True),
        sa.Column("codigo_numerico", sa.String(8), nullable=True),
        sa.Column("cuf", sa.String(2), nullable=False),
        sa.Column("codigo_municipio_fato_gerador", sa.String(7), nullable=True),
        sa.Column("data_emissao", sa.DateTime(), nullable=False),
        sa.Column("data_saida_entrada", sa.DateTime(), nullable=True),
        sa.Column("protocolo_autorizacao", sa.String(30), nullable=True),
        sa.Column("data_autorizacao", sa.DateTime(), nullable=True),
        sa.Column("codigo_status_sefaz", sa.String(10), nullable=True),
        sa.Column("motivo_status", sa.Text(), nullable=True),
        sa.Column("observacoes_fisco", sa.Text(), nullable=True),
        sa.Column("informacoes_complementares", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "empresa_emitente_id", "modelo", "serie", "numero",
            name="uq_fiscal_documento_numero",
        ),
    )
    op.create_index("ix_fiscal_documentos_tenant_status", "fiscal_documentos", ["tenant_id", "status"])
    op.create_index("ix_fiscal_documentos_pedido", "fiscal_documentos", ["pedido_id"])
    op.create_index("ix_fiscal_documentos_chave", "fiscal_documentos", ["chave_acesso"])

    # 2. fiscal_documento_emitente_snapshot
    op.create_table(
        "fiscal_documento_emitente_snapshot",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fiscal_documento_id", sa.BigInteger(), nullable=False),
        sa.Column("razao_social", sa.String(255), nullable=False),
        sa.Column("nome_fantasia", sa.String(255), nullable=True),
        sa.Column("cnpj", sa.String(14), nullable=False),
        sa.Column("ie", sa.String(20), nullable=True),
        sa.Column("im", sa.String(20), nullable=True),
        sa.Column("cnae", sa.String(10), nullable=True),
        sa.Column("crt", sa.String(1), nullable=False),
        sa.Column("crt_descricao", sa.String(80), nullable=True),
        sa.Column("logradouro", sa.String(255), nullable=False),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("complemento", sa.String(120), nullable=True),
        sa.Column("bairro", sa.String(120), nullable=False),
        sa.Column("codigo_municipio_ibge", sa.String(7), nullable=False),
        sa.Column("municipio", sa.String(120), nullable=False),
        sa.Column("uf", sa.String(2), nullable=False),
        sa.Column("cep", sa.String(8), nullable=False),
        sa.Column("codigo_pais", sa.String(4), nullable=False, server_default="1058"),
        sa.Column("pais", sa.String(60), nullable=False, server_default="BRASIL"),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("logo_url_snapshot", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["fiscal_documento_id"], ["fiscal_documentos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fiscal_documento_id", name="uq_fiscal_doc_emitente_snapshot_doc_id"),
    )

    # 3. fiscal_documento_destinatario_snapshot
    op.create_table(
        "fiscal_documento_destinatario_snapshot",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fiscal_documento_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo_pessoa", sa.String(10), nullable=False),
        sa.Column("nome_razao_social", sa.String(255), nullable=False),
        sa.Column("cpf", sa.String(11), nullable=True),
        sa.Column("cnpj", sa.String(14), nullable=True),
        sa.Column("ie", sa.String(20), nullable=True),
        sa.Column("ind_ie_dest", sa.String(1), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("logradouro", sa.String(255), nullable=False),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("complemento", sa.String(120), nullable=True),
        sa.Column("bairro", sa.String(120), nullable=False),
        sa.Column("codigo_municipio_ibge", sa.String(7), nullable=False),
        sa.Column("municipio", sa.String(120), nullable=False),
        sa.Column("uf", sa.String(2), nullable=False),
        sa.Column("cep", sa.String(8), nullable=False),
        sa.Column("codigo_pais", sa.String(4), nullable=False, server_default="1058"),
        sa.Column("pais", sa.String(60), nullable=False, server_default="BRASIL"),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(["fiscal_documento_id"], ["fiscal_documentos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fiscal_documento_id", name="uq_fiscal_doc_dest_snapshot_doc_id"),
    )

    # 4. fiscal_documento_itens
    op.create_table(
        "fiscal_documento_itens",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fiscal_documento_id", sa.BigInteger(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("produto_id", sa.BigInteger(), nullable=True),
        sa.Column("pedido_item_id", sa.BigInteger(), nullable=True),
        sa.Column("codigo_produto", sa.String(60), nullable=False),
        sa.Column("ean", sa.String(14), nullable=True),
        sa.Column("descricao", sa.String(255), nullable=False),
        sa.Column("ncm", sa.String(8), nullable=False),
        sa.Column("cest", sa.String(7), nullable=True),
        sa.Column("extipi", sa.String(3), nullable=True),
        sa.Column("cfop", sa.String(4), nullable=False),
        sa.Column("unidade_comercial", sa.String(6), nullable=False),
        sa.Column("quantidade_comercial", sa.Numeric(15, 4), nullable=False),
        sa.Column("valor_unitario_comercial", sa.Numeric(15, 10), nullable=False),
        sa.Column("valor_bruto", sa.Numeric(15, 2), nullable=False),
        sa.Column("ean_tributavel", sa.String(14), nullable=True),
        sa.Column("unidade_tributavel", sa.String(6), nullable=False),
        sa.Column("quantidade_tributavel", sa.Numeric(15, 4), nullable=False),
        sa.Column("valor_unitario_tributavel", sa.Numeric(15, 10), nullable=False),
        sa.Column("valor_frete", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_seguro", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_desconto", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_outras_despesas", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("indicador_total", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["fiscal_documento_id"], ["fiscal_documentos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fiscal_documento_id", "ordem", name="uq_fiscal_documento_item_ordem"),
    )

    # 5. fiscal_documento_item_impostos
    op.create_table(
        "fiscal_documento_item_impostos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fiscal_documento_item_id", sa.BigInteger(), nullable=False),
        sa.Column("origem_mercadoria", sa.String(1), nullable=False),
        sa.Column("cst_icms", sa.String(3), nullable=True),
        sa.Column("csosn", sa.String(3), nullable=True),
        sa.Column("modalidade_bc_icms", sa.String(1), nullable=True),
        sa.Column("base_icms", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("aliquota_icms", sa.Numeric(7, 4), nullable=False, server_default="0.0000"),
        sa.Column("valor_icms", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("modalidade_bc_icms_st", sa.String(1), nullable=True),
        sa.Column("base_icms_st", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("aliquota_icms_st", sa.Numeric(7, 4), nullable=False, server_default="0.0000"),
        sa.Column("valor_icms_st", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("base_fcp", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("aliquota_fcp", sa.Numeric(7, 4), nullable=False, server_default="0.0000"),
        sa.Column("valor_fcp", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("base_ipi", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("aliquota_ipi", sa.Numeric(7, 4), nullable=False, server_default="0.0000"),
        sa.Column("valor_ipi", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("cst_ipi", sa.String(2), nullable=True),
        sa.Column("base_pis", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("aliquota_pis", sa.Numeric(7, 4), nullable=False, server_default="0.0000"),
        sa.Column("valor_pis", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("cst_pis", sa.String(2), nullable=True),
        sa.Column("base_cofins", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("aliquota_cofins", sa.Numeric(7, 4), nullable=False, server_default="0.0000"),
        sa.Column("valor_cofins", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("cst_cofins", sa.String(2), nullable=True),
        sa.Column("valor_aprox_tributos", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.ForeignKeyConstraint(["fiscal_documento_item_id"], ["fiscal_documento_itens.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fiscal_documento_item_id", name="uq_fiscal_doc_item_impostos_item_id"),
    )

    # 6. fiscal_documento_totais
    op.create_table(
        "fiscal_documento_totais",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fiscal_documento_id", sa.BigInteger(), nullable=False),
        sa.Column("base_icms", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_icms", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("base_icms_st", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_icms_st", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_fcp", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_produtos", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_frete", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_seguro", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_desconto", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_ii", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_ipi", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_ipi_devolvido", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_pis", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_cofins", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("outras_despesas", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_total_nota", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("valor_total_tributos_aprox", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.ForeignKeyConstraint(["fiscal_documento_id"], ["fiscal_documentos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fiscal_documento_id", name="uq_fiscal_documento_totais_doc_id"),
    )

    # 7. fiscal_documento_transporte
    op.create_table(
        "fiscal_documento_transporte",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fiscal_documento_id", sa.BigInteger(), nullable=False),
        sa.Column("modalidade_frete", sa.String(1), nullable=False, server_default="9"),
        sa.Column("transportadora_nome", sa.String(255), nullable=True),
        sa.Column("transportadora_cnpj", sa.String(14), nullable=True),
        sa.Column("transportadora_cpf", sa.String(11), nullable=True),
        sa.Column("transportadora_ie", sa.String(20), nullable=True),
        sa.Column("transportadora_endereco", sa.String(255), nullable=True),
        sa.Column("transportadora_municipio", sa.String(120), nullable=True),
        sa.Column("transportadora_uf", sa.String(2), nullable=True),
        sa.Column("codigo_antt", sa.String(20), nullable=True),
        sa.Column("placa_veiculo", sa.String(8), nullable=True),
        sa.Column("uf_veiculo", sa.String(2), nullable=True),
        sa.Column("quantidade_volumes", sa.Numeric(15, 3), nullable=True),
        sa.Column("especie", sa.String(60), nullable=True),
        sa.Column("marca", sa.String(60), nullable=True),
        sa.Column("numeracao", sa.String(60), nullable=True),
        sa.Column("peso_bruto", sa.Numeric(15, 3), nullable=True),
        sa.Column("peso_liquido", sa.Numeric(15, 3), nullable=True),
        sa.ForeignKeyConstraint(["fiscal_documento_id"], ["fiscal_documentos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fiscal_documento_id", name="uq_fiscal_documento_transporte_doc_id"),
    )

    # 8. fiscal_documento_duplicatas
    op.create_table(
        "fiscal_documento_duplicatas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fiscal_documento_id", sa.BigInteger(), nullable=False),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("data_vencimento", sa.Date(), nullable=False),
        sa.Column("valor", sa.Numeric(15, 2), nullable=False),
        sa.ForeignKeyConstraint(["fiscal_documento_id"], ["fiscal_documentos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 9. fiscal_xml_store
    op.create_table(
        "fiscal_xml_store",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fiscal_documento_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo_xml", sa.String(20), nullable=False),
        sa.Column("versao_layout", sa.String(10), nullable=False),
        sa.Column("ambiente", sa.SmallInteger(), nullable=False),
        sa.Column("conteudo_xml", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("tamanho_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["fiscal_documento_id"], ["fiscal_documentos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fiscal_xml_store_documento_tipo",
        "fiscal_xml_store",
        ["fiscal_documento_id", "tipo_xml"],
    )

    # 10. fiscal_eventos (eventos do documento fiscal_documentos; tabela legado é fiscal_evento)
    op.create_table(
        "fiscal_eventos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("fiscal_documento_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo_evento", sa.String(30), nullable=False),
        sa.Column("codigo_status", sa.String(10), nullable=True),
        sa.Column("descricao_status", sa.Text(), nullable=True),
        sa.Column("protocolo", sa.String(30), nullable=True),
        sa.Column("xml_evento_id", sa.BigInteger(), nullable=True),
        sa.Column("xml_retorno_id", sa.BigInteger(), nullable=True),
        sa.Column("ocorrido_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("criado_por_usuario_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["fiscal_documento_id"], ["fiscal_documentos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["xml_evento_id"], ["fiscal_xml_store.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["xml_retorno_id"], ["fiscal_xml_store.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fiscal_eventos_documento", "fiscal_eventos", ["fiscal_documento_id", "ocorrido_em"])


def downgrade() -> None:
    op.drop_index("ix_fiscal_eventos_documento", table_name="fiscal_eventos")
    op.drop_table("fiscal_eventos")

    op.drop_index("ix_fiscal_xml_store_documento_tipo", table_name="fiscal_xml_store")
    op.drop_table("fiscal_xml_store")

    op.drop_table("fiscal_documento_duplicatas")
    op.drop_table("fiscal_documento_transporte")
    op.drop_table("fiscal_documento_totais")
    op.drop_table("fiscal_documento_item_impostos")
    op.drop_table("fiscal_documento_itens")
    op.drop_table("fiscal_documento_destinatario_snapshot")
    op.drop_table("fiscal_documento_emitente_snapshot")

    op.drop_index("ix_fiscal_documentos_chave", table_name="fiscal_documentos")
    op.drop_index("ix_fiscal_documentos_pedido", table_name="fiscal_documentos")
    op.drop_index("ix_fiscal_documentos_tenant_status", table_name="fiscal_documentos")
    op.drop_table("fiscal_documentos")
