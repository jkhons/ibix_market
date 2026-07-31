"""LGPD: Cliente Administrador pode visualizar PII de clientes do tenant.

Revision ID: br36_ca_pii_visualizar
Revises: br35_rls_policies
Create Date: 2026-06-18
"""
import sqlalchemy as sa
from alembic import op

revision = "br36_ca_pii_visualizar"
down_revision = "br35_rls_policies"
branch_labels = None
depends_on = None

PERMISSAO_PII = "pii:visualizar"
ROLE_CA = "Cliente Administrador"


def upgrade() -> None:
    conn = op.get_bind()
    perm_row = conn.execute(sa.text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_PII}).fetchone()
    role_row = conn.execute(sa.text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_CA}).fetchone()
    if not perm_row or not role_row:
        return
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
    role_row = conn.execute(sa.text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_CA}).fetchone()
    if perm_row and role_row:
        conn.execute(
            sa.text("DELETE FROM role_permissoes WHERE role_id = :r AND permissao_id = :p"),
            {"r": role_row[0], "p": perm_row[0]},
        )
