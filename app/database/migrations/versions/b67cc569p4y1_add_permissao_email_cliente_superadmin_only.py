"""Adicionar permissão email_cliente e restringir a Superadministrador

Revision ID: b67cc569p4y1
Revises: a56bb458o3x0
Create Date: 2026-02-08

Cria a permissão email_cliente (configuração de e-mail por cliente).
Não atribui a nenhuma role: Superadministrador já recebe todas as permissões por código.
Remove a permissão das roles Administrador e Cliente Administrador caso exista vínculo
(por migração anterior ou seed), garantindo que apenas Superadministrador tenha acesso.
"""
from alembic import op
from sqlalchemy import text

revision = "b67cc569p4y1"
down_revision = "a56bb458o3x0"
branch_labels = None
depends_on = None

PERMISSAO_NOME = "email_cliente"
PERMISSAO_DESCRICAO = "Configuração de e-mail por cliente (remetente por cliente)"
MODULO = "configuracoes"
ACAO = "visualizar"

ROLES_SEM_ACESSO = ["Administrador", "Cliente Administrador"]


def upgrade() -> None:
    conn = op.get_bind()
    # Inserir permissão se não existir
    r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME}).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                VALUES (:nome, :descricao, :modulo, :acao, true, NOW(), NOW())
            """),
            {"nome": PERMISSAO_NOME, "descricao": PERMISSAO_DESCRICAO, "modulo": MODULO, "acao": ACAO},
        )
    # Remover permissão das roles Administrador e Cliente Administrador
    perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME}).fetchone()
    if perm_row:
        permissao_id = perm_row[0]
        for role_nome in ROLES_SEM_ACESSO:
            role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
            if role_row:
                conn.execute(
                    text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
                    {"rid": role_row[0], "pid": permissao_id},
                )


def downgrade() -> None:
    conn = op.get_bind()
    perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME}).fetchone()
    if perm_row:
        conn.execute(text("DELETE FROM role_permissoes WHERE permissao_id = :pid"), {"pid": perm_row[0]})
        conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME})
