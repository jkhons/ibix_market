"""Seed role Operador PDV e permissões (Fase 1 - Plano PDV Hierarquia).

Revision ID: cc22ee469u8
Revises: bb11dd358t7
Create Date: 2026-02-18

Operador PDV: vendas no PDV, consulta estoque, fechamento de caixa, sangria/suprimento.
Sem relatórios gerenciais, custos globais, configurações fiscais.
"""
from alembic import op
from sqlalchemy import text

revision = "cc22ee469u8"
down_revision = "bb11dd358t7"
branch_labels = None
depends_on = None

ROLE_NOME = "Operador PDV"
ROLE_DESCRICAO = "Operação de caixa e vendas no PDV; consulta estoque; fechamento de caixa; sangria/suprimento com senha. Sem relatórios gerenciais nem configurações fiscais."

# (nome, descricao, modulo, acao)
PERMISSOES = [
    ("pdv:operar", "Operar PDV (vendas, caixa)", "pdv", "operar"),
    ("pdv:vendas", "Realizar vendas no PDV", "pdv", "vendas"),
    ("pdv:estoque_consultar", "Consultar estoque no PDV", "pdv", "estoque_consultar"),
    ("pdv:caixa_fechar", "Fechar caixa (turno)", "pdv", "caixa_fechar"),
    ("pdv:sangria_suprimento", "Sangria e suprimento (com senha)", "pdv", "sangria_suprimento"),
]


def upgrade() -> None:
    conn = op.get_bind()
    r = conn.execute(text("SELECT 1 FROM roles WHERE nome = :n"), {"n": ROLE_NOME}).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO roles (nome, descricao, ativo, created_at, updated_at)
                VALUES (:nome, :descricao, true, NOW(), NOW())
            """),
            {"nome": ROLE_NOME, "descricao": ROLE_DESCRICAO},
        )
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_NOME}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]

    for nome, descricao, modulo, acao in PERMISSOES:
        r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if not r:
            conn.execute(
                text("""
                    INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                    VALUES (:nome, :descricao, :modulo, :acao, true, NOW(), NOW())
                """),
                {"nome": nome, "descricao": descricao, "modulo": modulo, "acao": acao},
            )
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if perm_row:
            rp = conn.execute(
                text("SELECT 1 FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
                {"rid": role_id, "pid": perm_row[0]},
            ).fetchone()
            if not rp:
                conn.execute(
                    text("""
                        INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                        VALUES (:role_id, :permissao_id, NOW(), NOW())
                    """),
                    {"role_id": role_id, "permissao_id": perm_row[0]},
                )


def downgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_NOME}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]
    for nome, _, _, _ in PERMISSOES:
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if perm_row:
            conn.execute(
                text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
                {"rid": role_id, "pid": perm_row[0]},
            )
    conn.execute(text("DELETE FROM roles WHERE nome = :n"), {"n": ROLE_NOME})
    for nome in [p[0] for p in PERMISSOES]:
        conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": nome})
