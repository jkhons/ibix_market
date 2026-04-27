"""seed permissoes alinhadas ao sidebar (dashboard, clientes, negocios, fiscal, qualidade, etc.)

Revision ID: m22oo024i9p3
Revises: l11nn913h8o2
Create Date: 2026-02-08

Insere todas as permissões cujas chaves o sidebar usa para exibir/ocultar itens do menu.
Atribui essas permissões às roles Superadministrador e Administrador.
"""
from alembic import op
from sqlalchemy import text

revision = "m22oo024i9p3"
down_revision = "l11nn913h8o2"
branch_labels = None
depends_on = None

# (nome, descricao, modulo, acao) - nome deve coincidir com a chave usada no sidebar
PERMISSOES_SIDEBAR = [
    # Principal / Gestão
    ("dashboard", "Acessar dashboard principal", "dashboard", "visualizar"),
    ("clientes", "Acessar módulo de clientes", "clientes", "visualizar"),
    ("equipamentos", "Acessar módulo de equipamentos", "equipamentos", "visualizar"),
    ("agendamentos", "Acessar módulo de agendamento", "agendamentos", "visualizar"),
    ("contratos", "Acessar módulo de contratos", "contratos", "visualizar"),
    ("certificados", "Acessar módulo de certificados", "certificados", "visualizar"),
    # Fiscal
    ("fiscal.empresa", "Acessar dados da empresa (fiscal)", "fiscal", "empresa"),
    ("fiscal.notas-fiscais:visualizar", "Visualizar notas fiscais", "fiscal", "visualizar"),
    ("fiscal.notas-fiscais", "Acessar módulo de notas fiscais", "fiscal", "notas_fiscais"),
    # Negócios
    ("negocios.venda:visualizar", "Visualizar módulo de vendas", "negocios", "visualizar"),
    ("negocios.estoque:visualizar", "Visualizar módulo de estoque", "negocios", "visualizar"),
    ("negocios.financeiro:visualizar", "Visualizar módulo financeiro", "negocios", "visualizar"),
    ("negocios.ordem-servico:visualizar", "Visualizar ordens de serviço", "negocios", "visualizar"),
    ("negocios.lacres-selos:visualizar", "Visualizar lacres e selos", "negocios", "visualizar"),
    # Certificados auxiliares / Qualidade
    ("termobarohigrometro", "Acessar certificados auxiliares (termo-barômetro-higrômetro)", "qualidade", "visualizar"),
    ("peso", "Acessar certificados auxiliares (peso)", "qualidade", "visualizar"),
    ("inspetores", "Acessar certificados auxiliares (inspetores)", "qualidade", "visualizar"),
    # Qualidade (procedimentos, treinamentos, reclamações, auditorias, revisão)
    ("configuracoes", "Acessar configurações do sistema", "configuracoes", "visualizar"),
    ("calibracao", "Acessar procedimentos de calibração", "procedimentos", "visualizar"),
    ("afericao", "Acessar procedimentos de aferição", "procedimentos", "visualizar"),
]

ROLES_COM_TODAS_PERMISSOES = ["Superadministrador", "Administrador"]


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
    for nome, descricao, modulo, acao in PERMISSOES_SIDEBAR:
        _insert_permissao(conn, nome, descricao, modulo, acao)

    for role_nome in ROLES_COM_TODAS_PERMISSOES:
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for nome, _, _, _ in PERMISSOES_SIDEBAR:
            perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
            if not perm_row:
                continue
            _assign_permissao_to_role(conn, role_id, perm_row[0])


def downgrade() -> None:
    conn = op.get_bind()
    for role_nome in ROLES_COM_TODAS_PERMISSOES:
        role_row = conn.execute(text("SELECT id FROM roles WHERE nome = :n"), {"n": role_nome}).fetchone()
        if not role_row:
            continue
        role_id = role_row[0]
        for nome, _, _, _ in PERMISSOES_SIDEBAR:
            perm_row = conn.execute(text("SELECT id FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
            if not perm_row:
                continue
            conn.execute(
                text("DELETE FROM role_permissoes WHERE role_id = :rid AND permissao_id = :pid"),
                {"rid": role_id, "pid": perm_row[0]},
            )
    for nome, _, _, _ in PERMISSOES_SIDEBAR:
        try:
            conn.execute(text("DELETE FROM permissoes WHERE nome = :n"), {"n": nome})
        except Exception:
            pass
