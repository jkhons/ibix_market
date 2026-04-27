"""Atribui certificacao:relatorios:visualizar a Cliente Administrador (E-Relatórios).

Revision ID: d88gg168r7p5
Revises: c78ff057s7o4
Create Date: 2026-02-08

A permissão já existe (b67dd569q5a2). Esta migração garante que as roles
Superadministrador, Administrador e Cliente Administrador tenham a permissão
certificacao:relatorios:visualizar (busca por nome da role, sem IDs fixos).
"""
from alembic import op
from sqlalchemy import text

revision = "d88gg168r7p5"
down_revision = "c78ff057s7o4"
branch_labels = None
depends_on = None

PERM_NOME = "certificacao:relatorios:visualizar"
ROLES_COM_ACESSO_RELATORIOS = ["Superadministrador", "Administrador", "Cliente Administrador"]


def upgrade() -> None:
    conn = op.get_bind()
    perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERM_NOME}).fetchone()
    if not perm_row:
        return
    perm_id = perm_row[0]
    for role_nome in ROLES_COM_ACESSO_RELATORIOS:
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        rp = conn.execute(
            text("SELECT 1 FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_row[0], "pid": perm_id},
        ).fetchone()
        if not rp:
            conn.execute(
                text("""
                    INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                    VALUES (:role_id, :permissao_id, NOW(), NOW())
                """),
                {"role_id": role_row[0], "permissao_id": perm_id},
            )


def downgrade() -> None:
    conn = op.get_bind()
    perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERM_NOME}).fetchone()
    if not perm_row:
        return
    for role_nome in ROLES_COM_ACESSO_RELATORIOS:
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if role_row:
            conn.execute(
                text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
                {"rid": role_row[0], "pid": perm_row[0]},
            )
