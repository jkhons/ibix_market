"""Cria tabela templates_contratos para templates de contratos reutilizáveis

Revision ID: a67tt801j1u5
Revises: e99hh279s8q6
Create Date: 2026-02-09

A API /api/v1/templates-contratos e a página /contratos/tipos dependem desta tabela.
Modelo: app.models.template_contrato.TemplateContrato
"""
from alembic import op
from sqlalchemy import text

revision = "a67tt801j1u5"
down_revision = "e99hh279s8q6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Tipo do contrato: calibracao, afericao, manutencao, inspecao, outros
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS templates_contratos (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200) NOT NULL,
            descricao TEXT,
            conteudo TEXT NOT NULL,
            tipo_contrato VARCHAR(50) NOT NULL DEFAULT 'calibracao',
            ativo BOOLEAN NOT NULL DEFAULT true,
            created_by INTEGER,
            updated_by INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_templates_contratos_tipo ON templates_contratos (tipo_contrato)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_templates_contratos_ativo ON templates_contratos (ativo)"))


def downgrade() -> None:
    op.drop_table("templates_contratos", if_exists=True)
