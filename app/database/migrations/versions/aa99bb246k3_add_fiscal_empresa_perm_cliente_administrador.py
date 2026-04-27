"""Adiciona permissão fiscal.empresa à role Cliente Administrador.

Revision ID: aa99bb246k3
Revises: a78cd580j5k2
Create Date: 2026-02-08

Permite que Cliente Administrador acesse a página e o módulo Empresa Fiscal,
para ver e editar o próprio cadastro (dados obrigatórios para NF, certificados).
Cada CA mantém escopo isolado (cliente_administrador_clientes).
"""
from alembic import op
from sqlalchemy import text

revision = "aa99bb246k3"
down_revision = "a78cd580j5k2"
branch_labels = None
depends_on = None

ROLE_CLIENTE_ADMIN = "Cliente Administrador"
PERMISSAO_FISCAL_EMPRESA = "fiscal.empresa"


def upgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(
        text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_CLIENTE_ADMIN}
    ).fetchone()
    if not role_row:
        return
    role_id = role_row[0]

    perm_row = conn.execute(
        text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_FISCAL_EMPRESA}
    ).fetchone()
    if not perm_row:
        return

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


def downgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(
        text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_CLIENTE_ADMIN}
    ).fetchone()
    if not role_row:
        return
    perm_row = conn.execute(
        text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_FISCAL_EMPRESA}
    ).fetchone()
    if not perm_row:
        return
    conn.execute(
        text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
        {"rid": role_row[0], "pid": perm_row[0]},
    )
