"""add cliente_id to qualidade (procedimentos_metodo, auditorias_internas, revisoes_direcao)

Revision ID: q66rr468e8s2
Revises: p55rr357j2s6
Create Date: 2026-02-08

Isola dados do módulo qualidade por cliente (multi-tenant).
"""
import sqlalchemy as sa
from alembic import op

revision = "q66rr468e8s2"
down_revision = "p55rr357j2s6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # procedimentos_metodo: add cliente_id e trocar unique codigo por (cliente_id, codigo)
    op.add_column(
        "procedimentos_metodo",
        sa.Column("cliente_id", sa.Integer(), nullable=True, comment="Cliente dono do procedimento (escopo)"),
    )
    op.create_foreign_key(
        "fk_procedimentos_metodo_cliente",
        "procedimentos_metodo",
        "clientes",
        ["cliente_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_procedimentos_metodo_cliente_id", "procedimentos_metodo", ["cliente_id"])
    op.drop_constraint("uq_procedimentos_metodo_codigo", "procedimentos_metodo", type_="unique")
    op.create_index("uq_procedimentos_metodo_cliente_codigo", "procedimentos_metodo", ["cliente_id", "codigo"], unique=True)

    # auditorias_internas: add cliente_id e trocar unique numero por (cliente_id, numero)
    op.add_column(
        "auditorias_internas",
        sa.Column("cliente_id", sa.Integer(), nullable=True, comment="Cliente dono do registro (escopo)"),
    )
    op.create_foreign_key(
        "fk_auditorias_internas_cliente",
        "auditorias_internas",
        "clientes",
        ["cliente_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_auditorias_internas_cliente_id", "auditorias_internas", ["cliente_id"])
    op.drop_constraint("uq_auditorias_internas_numero", "auditorias_internas", type_="unique")
    op.create_index("uq_auditorias_internas_cliente_numero", "auditorias_internas", ["cliente_id", "numero"], unique=True)

    # revisoes_direcao
    op.add_column(
        "revisoes_direcao",
        sa.Column("cliente_id", sa.Integer(), nullable=True, comment="Cliente dono do registro (escopo)"),
    )
    op.create_foreign_key(
        "fk_revisoes_direcao_cliente",
        "revisoes_direcao",
        "clientes",
        ["cliente_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_revisoes_direcao_cliente_id", "revisoes_direcao", ["cliente_id"])


def downgrade() -> None:
    op.drop_index("idx_revisoes_direcao_cliente_id", "revisoes_direcao")
    op.drop_constraint("fk_revisoes_direcao_cliente", "revisoes_direcao", type_="foreignkey")
    op.drop_column("revisoes_direcao", "cliente_id")

    op.drop_index("uq_auditorias_internas_cliente_numero", "auditorias_internas")
    op.create_unique_constraint("uq_auditorias_internas_numero", "auditorias_internas", ["numero"])
    op.drop_index("idx_auditorias_internas_cliente_id", "auditorias_internas")
    op.drop_constraint("fk_auditorias_internas_cliente", "auditorias_internas", type_="foreignkey")
    op.drop_column("auditorias_internas", "cliente_id")

    op.drop_index("uq_procedimentos_metodo_cliente_codigo", "procedimentos_metodo")
    op.create_unique_constraint("uq_procedimentos_metodo_codigo", "procedimentos_metodo", ["codigo"])
    op.drop_index("idx_procedimentos_metodo_cliente_id", "procedimentos_metodo")
    op.drop_constraint("fk_procedimentos_metodo_cliente", "procedimentos_metodo", type_="foreignkey")
    op.drop_column("procedimentos_metodo", "cliente_id")
