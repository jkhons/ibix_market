"""Garantir que todos os módulos tenham permissões cadastradas (visualizar, criar, editar, excluir)

Revision ID: p55rr357j2s6
Revises: o44qq246i1r5
Create Date: 2026-02-08

Para cada módulo do sistema, insere as 4 permissões padrão se ainda não existirem.
Não remove nem altera permissões já existentes (ex.: usuarios:gerenciar_roles, fiscal:empresa).
"""
from alembic import op
from sqlalchemy import text

revision = "p55rr357j2s6"
down_revision = "o44qq246i1r5"
branch_labels = None
depends_on = None

# Módulos do sistema (coluna modulo na tabela permissoes)
MODULOS = [
    "dashboard",
    "clientes",
    "equipamentos",
    "agendamentos",
    "contratos",
    "certificados",
    "fiscal",
    "negocios",
    "qualidade",
    "configuracoes",
    "procedimentos",
    "usuarios",
]

# Ações padrão: (acao, descricao_template com {modulo})
ACOES_PADRAO = [
    ("visualizar", "Visualizar listagem de {modulo}"),
    ("criar", "Criar registros em {modulo}"),
    ("editar", "Editar registros em {modulo}"),
    ("excluir", "Excluir registros em {modulo}"),
]


def _insert_permissao_se_nao_existe(conn, nome: str, descricao: str, modulo: str, acao: str) -> None:
    r = conn.execute(text("SELECT 1 FROM permissoes WHERE nome = :n"), {"n": nome}).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO permissoes (nome, descricao, modulo, acao, ativo, created_at, updated_at)
                VALUES (:nome, :descricao, :modulo, :acao, true, NOW(), NOW())
            """),
            {"nome": nome, "descricao": descricao, "modulo": modulo, "acao": acao},
        )


def upgrade() -> None:
    conn = op.get_bind()
    for modulo in MODULOS:
        for acao, desc_template in ACOES_PADRAO:
            nome = f"{modulo}:{acao}"
            descricao = desc_template.format(modulo=modulo)
            _insert_permissao_se_nao_existe(conn, nome, descricao, modulo, acao)


def downgrade() -> None:
    # Não removemos as permissões no downgrade para evitar quebrar roles que já as usam.
    # Se precisar reverter, remova manualmente apenas as que foram criadas por esta migração.
    pass
