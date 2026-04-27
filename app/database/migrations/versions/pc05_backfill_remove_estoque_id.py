"""Backfill produto_cliente_id a partir do mapa e remover coluna estoque_id.

Para venda_itens, notas_fiscais_itens, cupons_fiscais_itens, ordem_servico_itens:
- Atualizar produto_cliente_id = mapa[estoque_id] onde estoque_id preenchido.
- Remover coluna estoque_id.

Revision ID: pc05_backfill
Revises: pc04_add_pcid
Create Date: 2026-03-03

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "pc05_backfill"
down_revision = "pc04_add_pcid"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Backfill usando migracao_estoque_produto_cliente_map
    for table, id_col in [
        ("venda_itens", "estoque_id"),
        ("notas_fiscais_itens", "estoque_id"),
        ("cupons_fiscais_itens", "estoque_id"),
        ("ordem_servico_itens", "estoque_id"),
    ]:
        conn.execute(
            text(
                f"UPDATE {table} SET produto_cliente_id = m.produto_cliente_id "
                f"FROM migracao_estoque_produto_cliente_map m "
                f"WHERE {table}.{id_col} = m.estoque_id AND {table}.{id_col} IS NOT NULL"
            )
        )

    # Remover FK e coluna estoque_id de cada tabela
    # venda_itens
    op.drop_constraint("venda_itens_estoque_id_fkey", "venda_itens", type_="foreignkey")
    op.drop_column("venda_itens", "estoque_id")

    # notas_fiscais_itens
    op.drop_constraint("notas_fiscais_itens_estoque_id_fkey", "notas_fiscais_itens", type_="foreignkey")
    op.drop_column("notas_fiscais_itens", "estoque_id")

    # cupons_fiscais_itens
    op.drop_constraint("cupons_fiscais_itens_estoque_id_fkey", "cupons_fiscais_itens", type_="foreignkey")
    op.drop_column("cupons_fiscais_itens", "estoque_id")

    # ordem_servico_itens
    op.drop_constraint("ordem_servico_itens_estoque_id_fkey", "ordem_servico_itens", type_="foreignkey")
    op.drop_column("ordem_servico_itens", "estoque_id")


def downgrade() -> None:
    # Re-adicionar colunas estoque_id (sem backfill reverso; não restaura valores)
    op.add_column("venda_itens", sa.Column("estoque_id", sa.Integer(), nullable=True))
    op.add_column("notas_fiscais_itens", sa.Column("estoque_id", sa.Integer(), sa.ForeignKey("estoque.id"), nullable=True))
    op.add_column("cupons_fiscais_itens", sa.Column("estoque_id", sa.Integer(), sa.ForeignKey("estoque.id"), nullable=True))
    op.add_column("ordem_servico_itens", sa.Column("estoque_id", sa.Integer(), sa.ForeignKey("estoque.id"), nullable=True))
    # Nota: downgrade não restaura os valores de estoque_id a partir do mapa.
    raise NotImplementedError("Downgrade não restaura estoque_id a partir do mapa.")

