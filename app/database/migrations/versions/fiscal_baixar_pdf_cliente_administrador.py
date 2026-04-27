"""Atribui permissão fiscal:baixar_pdf à role Cliente Administrador.

Revision ID: fiscal_baixar_pdf_ca
Revises: lg02_seed_entregador
Create Date: 2026-03-12

Permite que o Cliente Administrador baixe/visualize o PDF (DANFE) das notas fiscais
emitidas no seu escopo (ex.: Notas Fiscais > Ver nota renderizada / Baixar PDF).
A permissão fiscal:baixar_pdf já existe (criada em t99uu791h9q3 para Contador).
"""
from alembic import op
from sqlalchemy import text

revision = "fiscal_baixar_pdf_ca"
down_revision = "lg02_seed_entregador"
branch_labels = None
depends_on = None

ROLE_CLIENTE_ADMIN = "Cliente Administrador"
PERMISSAO_BAIXAR_PDF = "fiscal:baixar_pdf"


def upgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(
        text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_CLIENTE_ADMIN}
    ).fetchone()
    if not role_row:
        return
    role_id = role_row[0]

    perm_row = conn.execute(
        text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_BAIXAR_PDF}
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
        text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_BAIXAR_PDF}
    ).fetchone()
    if not perm_row:
        return
    conn.execute(
        text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
        {"rid": role_row[0], "pid": perm_row[0]},
    )
