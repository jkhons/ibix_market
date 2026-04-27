"""seed role Contador e permissoes fiscais (area do contador)

Revision ID: t99uu791h9q3
Revises: s88tt680g8p2
Create Date: 2026-02-08

Cria role Contador e permissões fiscal:visualizar_documentos, fiscal:baixar_xml,
fiscal:baixar_pdf, fiscal:exportar_relatorios; atribui a Contador + clientes:visualizar.
"""
from alembic import op
from sqlalchemy import text

revision = "t99uu791h9q3"
down_revision = "s88tt680g8p2"
branch_labels = None
depends_on = None

ROLE_CONTADOR = "Contador"
ROLE_DESCRICAO = "Visão e exportação fiscal; sem poder editar/cancelar notas. Área do contador."

# (nome, descricao, modulo, acao)
PERMISSOES_FISCAL_CONTADOR = [
    ("fiscal:visualizar_documentos", "Visualizar documentos fiscais (área do contador)", "fiscal", "visualizar_documentos"),
    ("fiscal:baixar_xml", "Baixar XML de documentos fiscais", "fiscal", "baixar_xml"),
    ("fiscal:baixar_pdf", "Baixar PDF de documentos fiscais", "fiscal", "baixar_pdf"),
    ("fiscal:exportar_relatorios", "Exportar relatórios fiscais (CSV/Excel)", "fiscal", "exportar_relatorios"),
]

# Permissão existente (clientes:visualizar de p55) para Contador ter somente leitura de clientes
PERMISSAO_CLIENTES_VISUALIZAR = "clientes:visualizar"


def upgrade() -> None:
    conn = op.get_bind()
    # 1. Inserir role Contador se não existir
    r = conn.execute(text("SELECT 1 FROM roles WHERE nome = :n"), {"n": ROLE_CONTADOR}).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO roles (nome, descricao, ativo, created_at, updated_at)
                VALUES (:nome, :descricao, true, NOW(), NOW())
            """),
            {"nome": ROLE_CONTADOR, "descricao": ROLE_DESCRICAO},
        )
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_CONTADOR}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]

    # 2. Inserir permissões fiscais do contador
    for nome, descricao, modulo, acao in PERMISSOES_FISCAL_CONTADOR:
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

    # 3. Atribuir clientes:visualizar ao Contador (se a permissão existir)
    perm_clientes = conn.execute(
        text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_CLIENTES_VISUALIZAR}
    ).fetchone()
    if perm_clientes:
        rp = conn.execute(
            text("SELECT 1 FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_id, "pid": perm_clientes[0]},
        ).fetchone()
        if not rp:
            conn.execute(
                text("""
                    INSERT INTO role_permissoes (role_id, permissao_id, created_at, updated_at)
                    VALUES (:role_id, :permissao_id, NOW(), NOW())
                """),
                {"role_id": role_id, "permissao_id": perm_clientes[0]},
            )


def downgrade() -> None:
    conn = op.get_bind()
    role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": ROLE_CONTADOR}).fetchone()
    if not role_row:
        return
    role_id = role_row[0]
    for nome, _, _, _ in PERMISSOES_FISCAL_CONTADOR:
        perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
        if perm_row:
            conn.execute(
                text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
                {"rid": role_id, "pid": perm_row[0]},
            )
    perm_clientes = conn.execute(
        text("SELECT id FROM permissoes WHERE nome = :n"), {"n": PERMISSAO_CLIENTES_VISUALIZAR}
    ).fetchone()
    if perm_clientes:
        conn.execute(
            text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
            {"rid": role_id, "pid": perm_clientes[0]},
        )
    try:
        conn.execute(text("DELETE FROM roles WHERE nome = :n"), {"n": ROLE_CONTADOR})
    except Exception:
        pass
    for nome, _, _, _ in PERMISSOES_FISCAL_CONTADOR:
        try:
            conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": nome})
        except Exception:
            pass
