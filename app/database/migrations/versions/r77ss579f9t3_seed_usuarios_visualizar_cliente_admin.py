"""Atribuir permissoes usuarios (visualizar, criar, editar) à role Cliente Administrador

Revision ID: r77ss579f9t3
Revises: q66rr468e8s2
Create Date: 2026-02-08

Permite que Cliente Administrador acesse GET /api/v1/usuarios/ e gerencie usuários no seu escopo.
"""
from alembic import op
from sqlalchemy import text

revision = "r77ss579f9t3"
down_revision = "q66rr468e8s2"
branch_labels = None
depends_on = None

# Permissões que Cliente Administrador deve ter para gerenciar usuários (lista + criar/editar no escopo)
PERMISSOES_USUARIOS_CLIENTE_ADMIN = [
    "usuarios:visualizar",
    "usuarios:criar",
    "usuarios:editar",
]

ROLE_NOME = "Cliente Administrador"


def upgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_NOME}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]
    for nome in PERMISSOES_USUARIOS_CLIENTE_ADMIN:
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if not perm_row:
            continue
        permissao_id = perm_row[0]
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


def downgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_NOME}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]
    for nome in PERMISSOES_USUARIOS_CLIENTE_ADMIN:
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if not perm_row:
            continue
        conn.execute(
            text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_id, "pid": perm_row[0]},
        )
