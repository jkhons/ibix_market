"""modulo faturamento fiscal: empresa provedor, origem, ordem_servico_id, fiscal_evento, fiscal_download_log

Revision ID: s88tt680g8p2
Revises: r77ss579f9t3
Create Date: 2026-02-08

Estende Empresa (provedor + credenciais), NotaFiscal/NotaServico (origem, status RASCUNHO/ENVIADA),
NotaServico.ordem_servico_id, cria fiscal_evento e fiscal_download_log.
"""
import sqlalchemy as sa
from alembic import op

revision = "s88tt680g8p2"
down_revision = "r77ss579f9t3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Empresa: provedor fiscal e credenciais, série padrão
    op.add_column(
        "empresa",
        sa.Column("provedor_fiscal", sa.String(50), nullable=True, comment="Provedor fiscal (ex: nfs-e_nacional, focus_nfe, outro)"),
    )
    op.add_column(
        "empresa",
        sa.Column("provedor_api_key_encrypted", sa.Text(), nullable=True, comment="API key do provedor (criptografada)"),
    )
    op.add_column(
        "empresa",
        sa.Column("provedor_api_secret_encrypted", sa.Text(), nullable=True, comment="API secret do provedor (criptografada)"),
    )
    op.add_column(
        "empresa",
        sa.Column("serie_padrao_nfe", sa.String(10), nullable=True, server_default="1", comment="Série padrão NF-e"),
    )
    op.add_column(
        "empresa",
        sa.Column("serie_padrao_nfce", sa.String(10), nullable=True, server_default="1", comment="Série padrão NFC-e"),
    )

    # 2. notas_fiscais: origem_documento; status enum novos valores (PostgreSQL)
    op.add_column(
        "notas_fiscais",
        sa.Column("origem_documento", sa.String(30), nullable=True, comment="Origem do documento (manual, orcamento, venda_balcao, ordem_servico)"),
    )
    # Adicionar valores ao enum de status se for PostgreSQL
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("ALTER TYPE statusnotaenum ADD VALUE IF NOT EXISTS 'rascunho'")
        op.execute("ALTER TYPE statusnotaenum ADD VALUE IF NOT EXISTS 'enviada'")

    # 3. notas_servico: ordem_servico_id, origem_documento; status enum novos valores
    op.add_column(
        "notas_servico",
        sa.Column("ordem_servico_id", sa.Integer(), nullable=True, comment="ID da ordem de serviço (NFS-e gerada ao concluir OS)"),
    )
    op.add_column(
        "notas_servico",
        sa.Column("origem_documento", sa.String(30), nullable=True, comment="Origem do documento (manual, orcamento, venda_balcao, ordem_servico)"),
    )
    op.create_foreign_key(
        "fk_notas_servico_ordem_servico_id",
        "notas_servico",
        "ordem_servico",
        ["ordem_servico_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_notas_servico_ordem_servico", "notas_servico", ["ordem_servico_id"])
    op.create_index("idx_notas_servico_origem_documento", "notas_servico", ["origem_documento"])
    if conn.dialect.name == "postgresql":
        op.execute("ALTER TYPE statusnotaservicoenum ADD VALUE IF NOT EXISTS 'rascunho'")
        op.execute("ALTER TYPE statusnotaservicoenum ADD VALUE IF NOT EXISTS 'enviada'")

    op.create_index("idx_notas_fiscais_origem_documento", "notas_fiscais", ["origem_documento"])

    # 4. fiscal_evento
    op.create_table(
        "fiscal_evento",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("documento_tipo", sa.String(20), nullable=False, comment="Tipo do documento (nfse, nfe, nfce)"),
        sa.Column("documento_id", sa.Integer(), nullable=False, comment="ID da nota na tabela correspondente"),
        sa.Column("empresa_id", sa.Integer(), nullable=False, comment="ID da empresa emissora"),
        sa.Column("evento", sa.String(20), nullable=False, comment="Tipo do evento (envio, retorno, rejeicao, autorizacao, cancelamento)"),
        sa.Column("payload_raw", sa.Text(), nullable=True, comment="Payload raw retornado pelo provedor (JSON)"),
        sa.Column("usuario_id", sa.Integer(), nullable=True, comment="Usuário que disparou o evento"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        comment="Histórico de eventos fiscais (envio, retorno, rejeição, autorização, cancelamento)",
    )
    op.create_index("idx_fiscal_evento_documento", "fiscal_evento", ["documento_tipo", "documento_id"])
    op.create_index("idx_fiscal_evento_empresa", "fiscal_evento", ["empresa_id"])
    op.create_index("idx_fiscal_evento_evento", "fiscal_evento", ["evento"])
    op.create_index("idx_fiscal_evento_created_at", "fiscal_evento", ["created_at"])

    # 5. fiscal_download_log
    op.create_table(
        "fiscal_download_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False, comment="Usuário que fez o download"),
        sa.Column("documento_tipo", sa.String(20), nullable=False, comment="Tipo do documento (nfse, nfe, nfce)"),
        sa.Column("documento_id", sa.Integer(), nullable=False, comment="ID da nota na tabela correspondente"),
        sa.Column("arquivo_tipo", sa.String(10), nullable=False, comment="Tipo do arquivo (xml, pdf)"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        comment="Auditoria de downloads de XML/PDF de documentos fiscais",
    )
    op.create_index("idx_fiscal_download_log_usuario", "fiscal_download_log", ["usuario_id"])
    op.create_index("idx_fiscal_download_log_documento", "fiscal_download_log", ["documento_tipo", "documento_id"])
    op.create_index("idx_fiscal_download_log_created_at", "fiscal_download_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_fiscal_download_log_created_at", table_name="fiscal_download_log")
    op.drop_index("idx_fiscal_download_log_documento", table_name="fiscal_download_log")
    op.drop_index("idx_fiscal_download_log_usuario", table_name="fiscal_download_log")
    op.drop_table("fiscal_download_log")

    op.drop_index("idx_fiscal_evento_created_at", table_name="fiscal_evento")
    op.drop_index("idx_fiscal_evento_evento", table_name="fiscal_evento")
    op.drop_index("idx_fiscal_evento_empresa", table_name="fiscal_evento")
    op.drop_index("idx_fiscal_evento_documento", table_name="fiscal_evento")
    op.drop_table("fiscal_evento")

    op.drop_index("idx_notas_fiscais_origem_documento", table_name="notas_fiscais")
    op.drop_column("notas_fiscais", "origem_documento")

    op.drop_index("idx_notas_servico_origem_documento", table_name="notas_servico")
    op.drop_index("idx_notas_servico_ordem_servico", table_name="notas_servico")
    op.drop_constraint("fk_notas_servico_ordem_servico_id", "notas_servico", type_="foreignkey")
    op.drop_column("notas_servico", "origem_documento")
    op.drop_column("notas_servico", "ordem_servico_id")

    op.drop_column("empresa", "serie_padrao_nfce")
    op.drop_column("empresa", "serie_padrao_nfe")
    op.drop_column("empresa", "provedor_api_secret_encrypted")
    op.drop_column("empresa", "provedor_api_key_encrypted")
    op.drop_column("empresa", "provedor_fiscal")
