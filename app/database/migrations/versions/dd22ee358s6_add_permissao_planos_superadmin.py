"""Adicionar permissão planos (apenas Superadministrador)

Revision ID: dd22ee358s6
Revises: cc11dd247r5
Create Date: 2026-02-08

Cria a permissão planos:visualizar (módulo planos).
Superadministrador recebe todas as permissões por código (get_user_with_permissions).
Não atribui a outras roles; apenas Superadministrador terá acesso à página Planos.
"""
from alembic import op
from sqlalchemy import text

revision = "dd22ee358s6"
down_revision = "cc11dd247r5"
branch_labels = None
depends_on = None

PERMISSAO_NOME = "planos:visualizar"
PERMISSAO_DESCRICAO = "Planos e assinatura SaaS (acesso à página Planos)"
MODULO = "planos"
ACAO = "visualizar"


def upgrade() -> None:
    conn = op.get_bind()
    r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME}).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                VALUES (:nome, :descricao, :modulo, :acao, true, NOW(), NOW())
            """),
            {"nome": PERMISSAO_NOME, "descricao": PERMISSAO_DESCRICAO, "modulo": MODULO, "acao": ACAO},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DELETE FROM role_permissoes WHERE permissao_id = (SELECT id FROM permissoes WHERE nome = :n)"), {"n": PERMISSAO_NOME})
    conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME})
