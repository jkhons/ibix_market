"""Seed permissões Orçamento e Pedido (negocios.orcamento, negocios.pedido) e atribuição às roles.

Revision ID: ww33xx137n3x1
Revises: or01pd02
Create Date: 2026-02-28

Insere permissões para o módulo Orçamento e Pedido e atribui a Superadministrador,
Administrador e Cliente Administrador, para exibição no sidebar e controle de acesso.
"""
from alembic import op
from sqlalchemy import text

revision = "ww33xx137n3x1"
down_revision = "or01pd02"
branch_labels = None
depends_on = None

PERMISSOES_ORCAMENTO_PEDIDO = [
    ("negocios.orcamento:visualizar", "Visualizar orçamentos", "negocios", "visualizar"),
    ("negocios.orcamento:criar", "Criar e editar orçamentos", "negocios", "criar"),
    ("negocios.pedido:visualizar", "Visualizar pedidos", "negocios", "visualizar"),
    ("negocios.pedido:criar", "Criar e editar pedidos", "negocios", "criar"),
    ("negocios.pedido:faturar", "Faturar pedidos", "negocios", "faturar"),
]

ROLES_COM_PERMISSAO = ["Superadministrador", "Administrador", "Cliente Administrador"]


def _insert_permissao(conn, nome, descricao, modulo, acao):
    r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                VALUES (:nome, :descricao, :modulo, :acao, true, NOW(), NOW())
            """),
            {"nome": nome, "descricao": descricao, "modulo": modulo, "acao": acao},
        )


def _assign_permissao_to_role(conn, role_id: int, permissao_id: int):
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


def upgrade() -> None:
    conn = op.get_bind()
    for nome, descricao, modulo, acao in PERMISSOES_ORCAMENTO_PEDIDO:
        _insert_permissao(conn, nome, descricao, modulo, acao)

    for role_nome in ROLES_COM_PERMISSAO:
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for nome, _, _, _ in PERMISSOES_ORCAMENTO_PEDIDO:
            perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
            if not perm_row:
                continue
            _assign_permissao_to_role(conn, role_id, perm_row[0])


def downgrade() -> None:
    conn = op.get_bind()
    for role_nome in ROLES_COM_PERMISSAO:
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for nome, _, _, _ in PERMISSOES_ORCAMENTO_PEDIDO:
            perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
            if not perm_row:
                continue
            conn.execute(
                text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
                {"rid": role_id, "pid": perm_row[0]},
            )
    for nome, _, _, _ in PERMISSOES_ORCAMENTO_PEDIDO:
        conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": nome})
