"""Remove permissões do módulo negocios.cadastro (página /negocio/cadastro descontinuada)

Revision ID: a56bb458o3x0
Revises: z45aa347n2w9
Create Date: 2026-02-08

Remove da base todas as permissões cujo nome começa com 'negocios.cadastro'
e os vínculos em role_permissoes, pois a página e o módulo foram removidos.
"""
from alembic import op
from sqlalchemy import text

revision = "a56bb458o3x0"
down_revision = "z45aa347n2w9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Remove vínculos de roles com permissões negocios.cadastro
    conn.execute(
        text("""
            DELETE FROM role_permissoes
            WHERE permissao_id IN (SELECT id FROM permissoes WHERE nome LIKE 'negocios.cadastro%')
        """)
    )
    # Remove as permissões do módulo negocios.cadastro
    conn.execute(text("DELETE FROM permissoes WHERE nome LIKE 'negocios.cadastro%'"))


def downgrade() -> None:
    # Não re-insere: o seed m22oo024i9p3 não inclui mais negocios.cadastro.
    # Para restaurar, seria necessário re-adicionar manualmente ao seed e rodar migração.
    pass
