"""Remover permissões de negócios da role Subcliente (Portal Cliente Final)

Revision ID: x34zz247m3v9
Revises: e02qq357m8t3
Create Date: 2026-02-12

Cliente final (Subcliente) não deve acessar Minhas vendas nem Resumo financeiro.
Remove da role Subcliente a permissão negocios.venda:visualizar.
"""
from alembic import op
from sqlalchemy import text

revision = "x34zz247m3v9"
down_revision = "e02qq357m8t3"
branch_labels = None
depends_on = None

# Permissões de negócios a remover da role Subcliente (não hardcode IDs)
PERMISSOES_NEGOCIOS_SUBCLIENTE = [
    "negocios.venda:visualizar",
]

ROLE_NOME = "Subcliente"


def upgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_NOME}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]
    for nome in PERMISSOES_NEGOCIOS_SUBCLIENTE:
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if not perm_row:
            continue
        permissao_id = perm_row[0]
        conn.execute(
            text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_id, "pid": permissao_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_NOME}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]
    for nome in PERMISSOES_NEGOCIOS_SUBCLIENTE:
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
