"""Seed permissões do módulo marketplace e atribuição a Superadministrador, Administrador e Cliente Administrador.

Revision ID: mk02_perm
Revises: mk01_tables
Create Date: 2026-03-07

Sem dados mockados: permissões inseridas por nome; roles e vínculos obtidos do banco.
"""
from alembic import op
from sqlalchemy import text

revision = "mk02_perm"
down_revision = "mk01_tables"
branch_labels = None
depends_on = None

MODULO = "marketplace"

PERMISSOES = [
    ("marketplace:visualizar", "Visualizar módulo e listagem da própria loja", "visualizar"),
    ("marketplace:publicar", "Publicar, editar e pausar anúncios", "publicar"),
    ("marketplace:gerenciar_pedidos", "Ver e atualizar status de pedidos da loja", "gerenciar_pedidos"),
    ("marketplace:financeiro", "Ver extrato e solicitar saque", "financeiro"),
    ("marketplace:configurar_loja", "Ativar e editar dados da loja", "configurar_loja"),
]

ROLES_COM_ACESSO = ["Superadministrador", "Administrador", "Cliente Administrador"]


def _insert_permissao(conn, nome, descricao, acao):
    r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                VALUES (:nome, :descricao, :modulo, :acao, true, NOW(), NOW())
            """),
            {"nome": nome, "descricao": descricao, "modulo": MODULO, "acao": acao},
        )


def _assign_to_roles(conn):
    for nome_perm, _, acao in PERMISSOES:
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome_perm}).fetchone()
        if not perm_row:
            continue
        permissao_id = perm_row[0]
        for role_nome in ROLES_COM_ACESSO:
            role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
            if not role_row:
                continue
            rp = conn.execute(
                text("SELECT 1 FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
                {"rid": role_row[0], "pid": permissao_id},
            ).fetchone()
            if not rp:
                conn.execute(
                    text("""
                        INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                        VALUES (:role_id, :permissao_id, NOW(), NOW())
                    """),
                    {"role_id": role_row[0], "permissao_id": permissao_id},
                )


def upgrade() -> None:
    conn = op.get_bind()
    for nome, descricao, acao in PERMISSOES:
        _insert_permissao(conn, nome, descricao, acao)
    _assign_to_roles(conn)


def downgrade() -> None:
    conn = op.get_bind()
    for nome_perm, _, _ in PERMISSOES:
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome_perm}).fetchone()
        if perm_row:
            conn.execute(text("DELETE FROM role_permissoes WHERE permissao_id = :pid"), {"pid": perm_row[0]})
            conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": nome_perm})
