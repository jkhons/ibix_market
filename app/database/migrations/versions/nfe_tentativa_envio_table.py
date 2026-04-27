"""Cria tabela nfe_tentativa_envio (auditoria de tentativas NF-e SEFAZ).

Revision ID: nfe_tent_env
Revises: fiscal_evt_resp
Create Date: 2026-03-12

Entrega 5 plano estabilização NF-e: registro de cada tentativa com tipo_erro,
servico, cert_serial, xml_hash_sha256, duracao_ms, http_content_type, etc.
"""
import sqlalchemy as sa
from alembic import op

revision = "nfe_tent_env"
down_revision = "fiscal_evt_resp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nfe_tentativa_envio",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("nota_fiscal_id", sa.Integer(), nullable=False, comment="Nota fiscal enviada"),
        sa.Column("empresa_id", sa.Integer(), nullable=False, comment="Empresa emissora"),
        sa.Column("sucesso", sa.Boolean(), nullable=False, server_default=sa.false(), comment="True se autorizado/evento aceito"),
        sa.Column("status_http", sa.Integer(), nullable=True, comment="Código HTTP da resposta"),
        sa.Column("http_content_type", sa.String(100), nullable=True, comment="Content-Type do retorno"),
        sa.Column("tipo_erro", sa.String(50), nullable=True, comment="validacao, assinatura, ssl, rejeicao_fiscal, timeout, etc."),
        sa.Column("servico", sa.String(30), nullable=False, comment="autorizacao, cancelamento, etc."),
        sa.Column("ambiente_sefaz", sa.String(20), nullable=True, comment="homologacao ou producao"),
        sa.Column("mensagem", sa.Text(), nullable=True, comment="Mensagem de erro ou retorno"),
        sa.Column("cert_serial", sa.String(80), nullable=True, comment="Serial do certificado A1"),
        sa.Column("cert_subject", sa.String(255), nullable=True, comment="Subject do certificado (truncado)"),
        sa.Column("xml_hash_sha256", sa.String(64), nullable=True, comment="SHA-256 do XML assinado"),
        sa.Column("tentativa_numero", sa.Integer(), nullable=False, server_default=sa.text("1"), comment="Número da tentativa"),
        sa.Column("duracao_ms", sa.Integer(), nullable=True, comment="Duração da chamada em ms"),
        sa.Column("resposta_bruta", sa.Text(), nullable=True, comment="Resposta bruta SEFAZ (truncada)"),
        sa.Column("payload_retorno", sa.Text(), nullable=True, comment="JSON do retorno parseado"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["nota_fiscal_id"], ["notas_fiscais.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        comment="Auditoria de tentativas de envio NF-e à SEFAZ",
    )
    op.create_index("ix_nfe_tentativa_nota_empresa", "nfe_tentativa_envio", ["nota_fiscal_id", "empresa_id"])
    op.create_index("ix_nfe_tentativa_created", "nfe_tentativa_envio", ["created_at"])
    op.create_index("ix_nfe_tentativa_envio_nota_fiscal_id", "nfe_tentativa_envio", ["nota_fiscal_id"])
    op.create_index("ix_nfe_tentativa_envio_empresa_id", "nfe_tentativa_envio", ["empresa_id"])


def downgrade() -> None:
    op.drop_index("ix_nfe_tentativa_envio_empresa_id", table_name="nfe_tentativa_envio")
    op.drop_index("ix_nfe_tentativa_envio_nota_fiscal_id", table_name="nfe_tentativa_envio")
    op.drop_index("ix_nfe_tentativa_created", table_name="nfe_tentativa_envio")
    op.drop_index("ix_nfe_tentativa_nota_empresa", table_name="nfe_tentativa_envio")
    op.drop_table("nfe_tentativa_envio")
