"""Atribuir permissões dos módulos negocios e pdv à role Cliente Administrador (CA).

Revision ID: ca_neg_pdv
Revises: pc04_cest
Create Date: 2026-03-03

Todo CA deve ter permissão de acessar Negócios (vendas, estoque, etc.) e PDV.
Usa permissoes existentes (modulo='negocios' e modulo='pdv') e vincula à role Cliente Administrador.
"""
from alembic import op
from sqlalchemy import text

revision = "ca_neg_pdv"
down_revision = "pc04_cest"
branch_labels = None
depends_on = None

ROLE_NOME = "Cliente Administrador"
MODULOS_OBRIGATORIOS_CA = ("negocios", "pdv")


def upgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_NOME}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]

    for modulo in MODULOS_OBRIGATORIOS_CA:
        perm_row = conn.execute(
            text("SELECT id FROM permissoes WHERE modulo = :mod AND ativo = true ORDER BY id LIMIT 1"),
            {"mod": modulo},
        ).fetchone()
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

    for modulo in MODULOS_OBRIGATORIOS_CA:
        perm_row = conn.execute(
            text("SELECT id FROM permissoes WHERE modulo = :mod LIMIT 1"),
            {"mod": modulo},
        ).fetchone()
        if not perm_row:
            continue
        conn.execute(
            text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_id, "pid": perm_row[0]},
        )
