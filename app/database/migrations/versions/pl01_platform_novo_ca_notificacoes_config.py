"""Plataforma: flags de notificação ao Superadmin quando novo CA se cadastra (e-mail + sino).

Revision ID: pl01_platform_novo_ca_notificacoes
Revises: or03_orcamento_conversao_os_venda
Create Date: 2026-05-12
"""
from alembic import op
from sqlalchemy import text

revision = "pl01_platform_novo_ca_notificacoes"
down_revision = "or03_orcamento_conversao_os_venda"
branch_labels = None
depends_on = None

CHAVES = (
    (
        "platform_novo_ca_email_enabled",
        "true",
        "Quando true, envia e-mail aos Superadministradores ao concluir cadastro público de lojista (CA).",
    ),
    (
        "platform_novo_ca_in_app_enabled",
        "true",
        "Quando true, grava notificação no sino (usuario_notificacoes) para cada Superadministrador.",
    ),
)


def upgrade() -> None:
    conn = op.get_bind()
    for chave, valor, descricao in CHAVES:
        r = conn.execute(
            text("SELECT 1 FROM configuracoes WHERE chave = :chave"),
            {"chave": chave},
        ).fetchone()
        if not r:
            conn.execute(
                text(
                    """
                    INSERT INTO configuracoes (chave, valor, descricao, created_at, updated_at)
                    VALUES (:chave, :valor, :descricao, NOW(), NOW())
                    """
                ),
                {"chave": chave, "valor": valor, "descricao": descricao},
            )


def downgrade() -> None:
    conn = op.get_bind()
    for chave, _, _ in CHAVES:
        conn.execute(text("DELETE FROM configuracoes WHERE chave = :chave"), {"chave": chave})
