"""Permissão fiscal.empresa.ver_cliente apenas para Superadministrador e Administrador.

Revision ID: w33xx126m2v8
Revises: c78ff057s7o4
Create Date: 2026-02-08

Cria a permissão fiscal.empresa.ver_cliente (visualizar campo Cliente na tela Empresa Fiscal).
Atribui apenas às roles Superadministrador e Administrador.
Cliente Administrador não vê o campo/coluna Cliente; o vínculo é definido automaticamente pelo escopo.
"""
from alembic import op
from sqlalchemy import text

revision = "w33xx126m2v8"
down_revision = "c78ff057s7o4"
branch_labels = None
depends_on = None

PERMISSAO_NOME = "fiscal.empresa.ver_cliente"
PERMISSAO_DESCRICAO = "Visualizar campo Cliente na tela Empresa Fiscal (apenas Administrador e Superadministrador)"
MODULO = "fiscal"
ACAO = "visualizar"

ROLES_COM_ACESSO = ["Superadministrador", "Administrador"]


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
