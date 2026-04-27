"""Cria tabela clientes se não existir (ausente nas migrações Alembic)

Revision ID: g66ii468d3j7
Revises: f55hh357c2i6
Create Date: 2026-02-06

A tabela clientes é usada pelo front em /clientes e pelas APIs /api/v1/clientes.
É referenciada por administrador_clientes, cliente_administrador_clientes, etc.
Após migração MySQL → PostgreSQL, esta migração garante que a tabela exista no banco.
"""
from alembic import op
from sqlalchemy import text

revision = "g66ii468d3j7"
down_revision = "f55hh357c2i6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            cnpj VARCHAR(18) NOT NULL UNIQUE,
            cep VARCHAR(9),
            endereco VARCHAR(500) NOT NULL,
            cidade VARCHAR(100) NOT NULL,
            uf VARCHAR(2) NOT NULL,
            contato VARCHAR(100) NOT NULL,
            telefone VARCHAR(20) NOT NULL,
            email VARCHAR(100) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_clientes_cnpj ON clientes (cnpj)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_clientes_cidade ON clientes (cidade)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_clientes_uf ON clientes (uf)"))


def downgrade() -> None:
    op.drop_table("clientes", if_exists=True)
