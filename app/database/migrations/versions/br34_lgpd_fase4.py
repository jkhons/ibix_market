"""Multi-brand Fase 4: LGPD — permissão pii:visualizar.

Revision ID: br34_lgpd_fase4
Revises: br33_performance_indexes
Create Date: 2026-06-18
"""
import sqlalchemy as sa
from alembic import op

revision = "br34_lgpd_fase4"
down_revision = "br33_performance_indexes"
branch_labels = None
depends_on = None

PERMISSAO_PII = "pii:visualizar"
ROLES_COM_PII = ("Superadministrador", "Administrador")


def upgrade() -> None:
    conn = op.get_bind()
    r = conn.execute(sa.text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_PII}).fetchone()
    if not r:
        conn.execute(
            sa.text(
                """
                INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                VALUES (:nome, :descricao, 'pii', 'visualizar', true, NOW(), NOW())
                """
            ),
            {
                "nome": PERMISSAO_PII,
                "descricao": "Visualizar e alterar PII (CPF, RG, documento) de usuários",
            },
        )
    for role_nome in ROLES_COM_PII:
        role_row = conn.execute(sa.text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        perm_row = conn.execute(sa.text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_PII}).fetchone()
        if not perm_row:
            continue
        exists = conn.execute(
            sa.text("SELECT 1 FROM role_permissoes WHERE role_id = :r AND permissao_id = :p"),
            {"r": role_row[0], "p": perm_row[0]},
        ).fetchone()
        if not exists:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                    VALUES (:r, :p, NOW(), NOW())
                    """
                ),
                {"r": role_row[0], "p": perm_row[0]},
            )


def downgrade() -> None:
    conn = op.get_bind()
    perm_row = conn.execute(sa.text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_PII}).fetchone()
    if perm_row:
        conn.execute(sa.text("DELETE FROM role_permissoes WHERE permissao_id = :p"), {"p": perm_row[0]})
        conn.execute(sa.text("DELETE FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_PII})
