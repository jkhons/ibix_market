"""Adiciona permissão configuracoes:whatsapp e atribui apenas à role Superadministrador.

Revision ID: a78dd581k6l3
Revises: z67bb569o5y1
Create Date: 2026-02-12

Módulo de configuração do WhatsApp (Integração WhatsApp Business Cloud API)
visível na gestão de funções/permissões apenas para Superadministrador.
"""
from alembic import op
from sqlalchemy import text

revision = "a78dd581k6l3"
down_revision = "z67bb569o5y1"
branch_labels = None
depends_on = None

PERMISSAO_NOME = "configuracoes:whatsapp"
PERMISSAO_DESCRICAO = "Configurar integração WhatsApp (Superadministrador)"
MODULO = "configuracoes"
ACAO = "whatsapp"


def upgrade() -> None:
    conn = op.get_bind()
    r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME}).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                VALUES (:nome, :descricao, :modulo, :acao, true, NOW(), NOW())
            """),
            {"nome": PERMISSAO_NOME, "descricao": PERMISSAO_DESCRICAO, "modulo": MODULO, "acao": ACAO},
        )

    # Atribuir apenas à role Superadministrador
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": "Superadministrador"}).fetchone()
    perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME}).fetchone()
    if role_row and perm_row:
        role_id, perm_id = role_row[0], perm_row[0]
        rp = conn.execute(
            text("SELECT 1 FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_id, "pid": perm_id},
        ).fetchone()
        if not rp:
            conn.execute(
                text("""
                    INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                    VALUES (:role_id, :permissao_id, NOW(), NOW())
                """),
                {"role_id": role_id, "permissao_id": perm_id},
            )


def downgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": "Superadministrador"}).fetchone()
    perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME}).fetchone()
    if role_row and perm_row:
        conn.execute(
            text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_row[0], "pid": perm_row[0]},
        )
    try:
        conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_NOME})
    except Exception:
        pass
