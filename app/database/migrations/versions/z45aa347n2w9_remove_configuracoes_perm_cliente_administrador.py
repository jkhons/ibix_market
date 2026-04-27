"""Remover permissões do módulo configuracoes da role Cliente Administrador

Revision ID: z45aa347n2w9
Revises: y34zz236m1v8
Create Date: 2026-02-08

Configurações do sistema fica apenas para Superadministrador e Administrador.
Remove qualquer permissão com modulo='configuracoes' da role Cliente Administrador.
"""
from alembic import op
from sqlalchemy import text

revision = "z45aa347n2w9"
down_revision = "y34zz236m1v8"
branch_labels = None
depends_on = None

ROLE_NOME = "Cliente Administrador"
MODULO_CONFIGURACOES = "configuracoes"


def upgrade() -> None:
    """Remove role_permissoes de configuracoes da role Cliente Administrador."""
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_NOME}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]
    conn.execute(
        text("""
            DELETE FROM role_permissoes
            WHERE role_id = :rid
            AND permissao_id IN (SELECT id FROM permissoes WHERE modulo = :mod)
        """),
        {"rid": role_id, "mod": MODULO_CONFIGURACOES},
    )


def downgrade() -> None:
    """Não reatribui: configuracoes permanece apenas para Superadministrador e Administrador."""
    pass
