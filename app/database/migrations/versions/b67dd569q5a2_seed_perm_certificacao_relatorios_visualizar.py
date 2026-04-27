"""seed permissão certificacao:relatorios:visualizar (E-Relatórios)

Revision ID: b67dd569q5a2
Revises: a56cc458p4z1
Create Date: 2026-02-08

Adiciona permissão certificacao:relatorios:visualizar e atribui a
Superadministrador e Administrador (MAPA_RBAC).
"""
from alembic import op
from sqlalchemy import text

revision = "b67dd569q5a2"
down_revision = "a56cc458p4z1"
branch_labels = None
depends_on = None

PERM_NOME = "certificacao:relatorios:visualizar"
PERM_DESCRICAO = "Visualizar e gerar relatórios de certificação"
PERM_MODULO = "certificacao"
PERM_ACAO = "relatorios:visualizar"

ROLES = ["Superadministrador", "Administrador"]


def upgrade() -> None:
    conn = op.get_bind()
    # 1. Inserir permissão se não existir
    r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": PERM_NOME}).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                VALUES (:nome, :descricao, :modulo, :acao, true, NOW(), NOW())
            """),
            {"nome": PERM_NOME, "descricao": PERM_DESCRICAO, "modulo": PERM_MODULO, "acao": PERM_ACAO},
        )
    perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERM_NOME}).fetchone()
    if not perm_row:
        return
    perm_id = perm_row[0]

    # 2. Atribuir às roles Superadministrador e Administrador
    for role_nome in ROLES:
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
    for role_nome in ROLES:
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if role_row:
            conn.execute(
                text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
                {"rid": role_row[0], "pid": perm_row[0]},
            )
    conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": PERM_NOME})
