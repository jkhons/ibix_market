"""Seed permissões do módulo afericoes (visualizar, criar, editar, excluir)

Revision ID: aa99bb691c5l1
Revises: a78cd580j5k2
Create Date: 2026-02-08

Insere afericoes:visualizar, afericoes:criar, afericoes:editar, afericoes:excluir.
Atribui às roles Superadministrador e Administrador (e Cliente Administrador conforme escopo).
"""
from alembic import op
from sqlalchemy import text

revision = "aa99bb691c5l1"
down_revision = "aa99bb246k3"
branch_labels = None
depends_on = None

MODULO = "afericoes"
PERMISSOES_AFERICOES = [
    ("afericoes:visualizar", "Visualizar listagem de aferições", "visualizar"),
    ("afericoes:criar", "Criar registros em aferições", "criar"),
    ("afericoes:editar", "Editar registros em aferições", "editar"),
    ("afericoes:excluir", "Excluir registros em aferições", "excluir"),
]

ROLES_COM_PERMISSAO = ["Superadministrador", "Administrador", "Cliente Administrador"]


def _insert_permissao(conn, nome: str, descricao: str, acao: str) -> None:
    r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                VALUES (:nome, :descricao, :modulo, :acao, true, NOW(), NOW())
            """),
            {"nome": nome, "descricao": descricao, "modulo": MODULO, "acao": acao},
        )


def _assign_permissao_to_role(conn, role_id: int, permissao_id: int) -> None:
    rp = conn.execute(
        text("SELECT 1 FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
        {"rid": role_id, "pid": permissao_id},
    ).fetchone()
    if not rp:
        conn.execute(
            text("""
                INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                VALUES (:role_id, :permissao_id, NOW(), NOW())
            """),
            {"role_id": role_id, "permissao_id": permissao_id},
        )


def upgrade() -> None:
    conn = op.get_bind()
    for nome, descricao, acao in PERMISSOES_AFERICOES:
        _insert_permissao(conn, nome, descricao, acao)

    for role_nome in ROLES_COM_PERMISSAO:
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for nome, _, _ in PERMISSOES_AFERICOES:
            perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
            if not perm_row:
                continue
            _assign_permissao_to_role(conn, role_id, perm_row[0])


def downgrade() -> None:
    conn = op.get_bind()
    for role_nome in ROLES_COM_PERMISSAO:
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for nome, _, _ in PERMISSOES_AFERICOES:
            perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
            if not perm_row:
                continue
            conn.execute(
                text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
                {"rid": role_id, "pid": perm_row[0]},
            )
    for nome, _, _ in PERMISSOES_AFERICOES:
        conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": nome})
