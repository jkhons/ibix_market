"""Permissão fiscal.empresa.configurar_provedor apenas para Superadministrador.

Revision ID: g77ff157s8o4
Revises: c78ff057s7o4
Create Date: 2026-02-08

Cria a permissão fiscal.empresa.configurar_provedor (configurar provedor fiscal na empresa).
Atribui apenas à role Superadministrador.
Administrador, Cliente Administrador e Técnico não veem nem podem alterar provedor/API key/séries.
"""
from alembic import op
from sqlalchemy import text

revision = "g77ff157s8o4"
down_revision = "c78ff057s7o4"
branch_labels = None
depends_on = None

PERMISSAO_NOME = "fiscal.empresa.configurar_provedor"
PERMISSAO_DESCRICAO = "Configurar provedor fiscal (provedor, API key, séries) - apenas Superadministrador"
MODULO = "fiscal"
ACAO = "configurar_provedor"

ROLES_COM_ACESSO = ["Superadministrador"]


def _insert_permissao(conn):
    r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME}).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                VALUES (:nome, :descricao, :modulo, :acao, true, NOW(), NOW())
            """),
            {"nome": PERMISSAO_NOME, "descricao": PERMISSAO_DESCRICAO, "modulo": MODULO, "acao": ACAO},
        )


def _assign_to_roles(conn):
    perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME}).fetchone()
    if not perm_row:
        return
    permissao_id = perm_row[0]
    for role_nome in ROLES_COM_ACESSO:
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        rp = conn.execute(
            text("SELECT 1 FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_row[0], "pid": permissao_id},
        ).fetchone()
        if not rp:
            conn.execute(
                text("""
                    INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                    VALUES (:role_id, :permissao_id, NOW(), NOW())
                """),
                {"role_id": role_row[0], "permissao_id": permissao_id},
            )


def upgrade() -> None:
    conn = op.get_bind()
    _insert_permissao(conn)
    _assign_to_roles(conn)


def downgrade() -> None:
    conn = op.get_bind()
    perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME}).fetchone()
    if perm_row:
        conn.execute(text("DELETE FROM role_permissoes WHERE permissao_id = :pid"), {"pid": perm_row[0]})
        conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME})
