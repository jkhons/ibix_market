"""Remover permissões usuarios (visualizar, criar, editar) da role Cliente Administrador

Revision ID: y34zz236m1v8
Revises: x23yy125l0u7
Create Date: 2026-02-08

Remove acesso à página /usuarios e à API /api/v1/usuarios para Cliente Administrador.
Gestão de sub-clientes e técnicos permanece em Minha equipe (/minha-equipe).
"""
from alembic import op
from sqlalchemy import text

revision = "y34zz236m1v8"
down_revision = "x23yy125l0u7"
branch_labels = None
depends_on = None

PERMISSOES_USUARIOS_REMOVER = [
    "usuarios:visualizar",
    "usuarios:criar",
    "usuarios:editar",
]
ROLE_NOME = "Cliente Administrador"


def upgrade() -> None:
    """Remove role_permissoes que dão à role Cliente Administrador acesso ao módulo usuarios."""
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_NOME}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]
    for nome in PERMISSOES_USUARIOS_REMOVER:
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if not perm_row:
            continue
        conn.execute(
            text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_id, "pid": perm_row[0]},
        )


def downgrade() -> None:
    """Reatribui permissoes usuarios (visualizar, criar, editar) à role Cliente Administrador."""
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_NOME}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]
    for nome in PERMISSOES_USUARIOS_REMOVER:
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if not perm_row:
            continue
        rp = conn.execute(
            text("SELECT 1 FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_id, "pid": perm_row[0]},
        ).fetchone()
        if not rp:
            conn.execute(
                text("""
                    INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                    VALUES (:role_id, :permissao_id, NOW(), NOW())
                """),
                {"role_id": role_id, "permissao_id": perm_row[0]},
            )
