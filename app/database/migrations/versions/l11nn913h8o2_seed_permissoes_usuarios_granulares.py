"""seed permissoes usuarios granulares (visualizar, criar, editar, excluir, gerenciar_roles)

Revision ID: l11nn913h8o2
Revises: k00mm802g7n1
Create Date: 2026-02-06

"""
from alembic import op
from sqlalchemy import text

revision = "l11nn913h8o2"
down_revision = "k00mm802g7n1"
branch_labels = None
depends_on = None

# Permissões granulares do módulo usuarios (autorização real; módulo não concede ações)
PERMISSOES_USUARIOS = [
    ("usuarios:visualizar", "Visualizar lista de usuários", "usuarios", "visualizar"),
    ("usuarios:criar", "Criar novos usuários", "usuarios", "criar"),
    ("usuarios:editar", "Editar usuários existentes", "usuarios", "editar"),
    ("usuarios:excluir", "Excluir usuários", "usuarios", "excluir"),
    ("usuarios:gerenciar_roles", "Gerenciar funções (roles) e permissões", "usuarios", "gerenciar_roles"),
]

ROLES_COM_PERMISSOES = ["Superadministrador", "Administrador"]


def upgrade() -> None:
    conn = op.get_bind()
    for nome, descricao, modulo, acao in PERMISSOES_USUARIOS:
        r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if not r:
            conn.execute(
                text("""
                    INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                    VALUES (:nome, :descricao, :modulo, :acao, true, NOW(), NOW())
                """),
                {"nome": nome, "descricao": descricao, "modulo": modulo, "acao": acao},
            )
    for role_nome in ROLES_COM_PERMISSOES:
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for nome, _, _, _ in PERMISSOES_USUARIOS:
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
    for role_nome in ROLES_COM_PERMISSOES:
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for nome, _, _, _ in PERMISSOES_USUARIOS:
            perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
            if not perm_row:
                continue
            conn.execute(
                text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
                {"rid": role_id, "pid": perm_row[0]},
            )
    for nome, _, _, _ in PERMISSOES_USUARIOS:
        try:
            conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": nome})
        except Exception:
            pass
