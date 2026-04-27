"""Atribuir permissões somente leitura à role Subcliente (Portal Subcliente)

Revision ID: d01pp246k7s2
Revises: c56ee135v7x0
Create Date: 2026-02-09

Portal Subcliente: acesso a dashboard, equipamentos, certificados, agendamentos (histórico),
vendas (visualizar). Sem create, update, delete.
"""
from alembic import op
from sqlalchemy import text

revision = "d01pp246k7s2"
down_revision = "c56ee135v7x0"
branch_labels = None
depends_on = None

# Permissões somente leitura para Subcliente (sidebar + API require_permission)
PERMISSOES_SUBCLIENTE = [
    "dashboard",
    "equipamentos",
    "equipamentos:visualizar",
    "certificados",
    "agendamentos",
    "agendamentos:visualizar",
    "negocios.venda:visualizar",
]

ROLE_NOME = "Subcliente"


def upgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_NOME}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]
    for nome in PERMISSOES_SUBCLIENTE:
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
    for nome in PERMISSOES_SUBCLIENTE:
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if not perm_row:
            continue
        conn.execute(
            text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_id, "pid": perm_row[0]},
        )
