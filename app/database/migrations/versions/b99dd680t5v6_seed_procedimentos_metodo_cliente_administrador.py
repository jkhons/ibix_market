"""Atribui qualidade:procedimentos_metodo:* a Cliente Administrador.

Revision ID: b99dd680t5v6
Revises: b89ab470n3x1
Create Date: 2026-02-09

Permite que Cliente Administrador acesse a página e a API de Procedimentos/Métodos
(/qualidade/procedimentos-metodo e GET/POST/PUT/DELETE /api/v1/procedimentos-metodo),
para cadastrar métodos utilizados em processos de calibração (escopo por cliente).
"""
from alembic import op
from sqlalchemy import text

revision = "b99dd680t5v6"
down_revision = "b89ab470n3x1"
branch_labels = None
depends_on = None

MODULO = "qualidade"
PERMISSOES = [
    ("qualidade:procedimentos_metodo:visualizar", "Visualizar procedimentos e métodos (ISO 17025 7.2)", "visualizar"),
    ("qualidade:procedimentos_metodo:criar", "Criar procedimentos e métodos", "criar"),
    ("qualidade:procedimentos_metodo:editar", "Editar procedimentos e métodos", "editar"),
    ("qualidade:procedimentos_metodo:excluir", "Excluir procedimentos e métodos", "excluir"),
]
ROLE_CA = "Cliente Administrador"


def upgrade() -> None:
    conn = op.get_bind()
    for nome, descricao, acao in PERMISSOES:
        r = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if not r:
            conn.execute(
                text("""
                    INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                    VALUES (:nome, :descricao, :modulo, :acao, true, NOW(), NOW())
                """),
                {"nome": nome, "descricao": descricao, "modulo": MODULO, "acao": acao},
            )
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if not perm_row:
            continue
        perm_id = perm_row[0]
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_CA}).fetchone()
        if not role_row:
            continue
        rp = conn.execute(
            text("SELECT 1 FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_row[0], "pid": perm_id},
        ).fetchone()
        if not rp:
            conn.execute(
                text("""
                    INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                    VALUES (:role_id, :permissao_id, NOW(), NOW())
                """),
                {"role_id": role_row[0], "permissao_id": perm_id},
            )


def downgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_CA}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]
    for nome, _, _ in PERMISSOES:
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if perm_row:
            conn.execute(
                text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
                {"rid": role_id, "pid": perm_row[0]},
            )
