"""seed roles Superadministrador e Cliente Administrador (Saas.md Fase 2)

Revision ID: c22ee024b9f3
Revises: b11de913c8a2
Create Date: 2026-02-06

"""
from alembic import op
from sqlalchemy import text

revision = "c22ee024b9f3"
down_revision = "b11de913c8a2"
branch_labels = None
depends_on = None

# Hierarquia: Superadministrador → Administrador → Cliente Administrador (e abaixo: Técnico, Cliente)
ROLES = [
    ("Superadministrador", "Controle total do sistema; gerencia administradores e configurações globais."),
    ("Administrador", "Administrador do sistema; gerencia clientes alocados e Cliente Administradores vinculados a ele."),
    ("Cliente Administrador", "Dono de um conjunto de clientes; cria técnicos e sub-clientes; vinculado a um Administrador."),
]


def upgrade() -> None:
    conn = op.get_bind()
    for nome, descricao in ROLES:
        r = conn.execute(text("SELECT 1 FROM roles WHERE nome = :n"), {"n": nome}).fetchone()
        if not r:
            conn.execute(
                text("""
                    INSERT INTO roles (nome, descricao, ativo, created_at, updated_at)
                    VALUES (:nome, :descricao, true, NOW(), NOW())
                """),
                {"nome": nome, "descricao": descricao},
            )


def downgrade() -> None:
    conn = op.get_bind()
    for nome, _ in ROLES:
        try:
            conn.execute(text("DELETE FROM roles WHERE nome = :n"), {"n": nome})
        except Exception:
            pass
