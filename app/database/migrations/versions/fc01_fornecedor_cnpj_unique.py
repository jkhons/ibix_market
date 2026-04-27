"""Fornecedor: unique parcial (cliente_id, cnpj), normalizar CNPJ existentes para digitos-only.

Revision ID: fc01_fornecedor_cnpj_uq
Revises: geo01_lat_lng
Create Date: 2026-04-15
"""
import sqlalchemy as sa
from alembic import op

revision = "fc01_fornecedor_cnpj_uq"
down_revision = "geo01_lat_lng"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    is_pg = conn.dialect.name == "postgresql"

    if is_pg:
        # 1) Normalizar CNPJs existentes para somente dígitos
        conn.execute(sa.text(
            "UPDATE fornecedores_cliente SET cnpj = regexp_replace(cnpj, '[^0-9]', '', 'g') "
            "WHERE cnpj IS NOT NULL AND cnpj != ''"
        ))

        # 2) Limpar CNPJs vazios para NULL (evitar conflito no unique)
        conn.execute(sa.text(
            "UPDATE fornecedores_cliente SET cnpj = NULL WHERE cnpj = ''"
        ))

        # 3) Resolver duplicatas: manter o mais recente (maior id), desativar os antigos
        conn.execute(sa.text("""
            UPDATE fornecedores_cliente SET ativo = false
            WHERE id IN (
                SELECT f1.id FROM fornecedores_cliente f1
                INNER JOIN fornecedores_cliente f2
                    ON f1.cliente_id = f2.cliente_id
                    AND f1.cnpj = f2.cnpj
                    AND f1.cnpj IS NOT NULL
                    AND f1.id < f2.id
            )
        """))

        # 4) Para duplicatas restantes (ambos ativos), excluir o mais antigo mantendo FK
        conn.execute(sa.text("""
            DELETE FROM fornecedores_cliente
            WHERE id IN (
                SELECT f1.id FROM fornecedores_cliente f1
                INNER JOIN fornecedores_cliente f2
                    ON f1.cliente_id = f2.cliente_id
                    AND f1.cnpj = f2.cnpj
                    AND f1.cnpj IS NOT NULL
                    AND f1.id < f2.id
                LEFT JOIN produtos_fornecedor pf ON pf.fornecedor_cliente_id = f1.id
                LEFT JOIN nfe_documentos nd ON nd.emitente_fornecedor_id = f1.id
                WHERE pf.id IS NULL AND nd.id IS NULL
            )
        """))

        # 5) Criar unique index parcial
        op.create_index(
            "uq_fornecedores_cliente_cnpj_por_estabelecimento",
            "fornecedores_cliente",
            ["cliente_id", "cnpj"],
            unique=True,
            postgresql_where=sa.text("cnpj IS NOT NULL AND cnpj != ''"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.drop_index(
            "uq_fornecedores_cliente_cnpj_por_estabelecimento",
            table_name="fornecedores_cliente",
        )
