"""Frete e transporte completo: formato_frete na loja, campos financeiros no pedido/extrato/repasse, tabela entregador_veiculos.

Revision ID: ft01_frete_transp
Revises: sp01_status_mk
Create Date: 2026-03-17
"""
import sqlalchemy as sa
from alembic import op

revision = "ft01_frete_transp"
down_revision = "sp01_status_mk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Loja: formato de frete
    op.add_column("lojas_marketplace", sa.Column("formato_frete", sa.String(20), nullable=False, server_default="sem_frete"))
    op.create_check_constraint(
        "ck_loja_formato_frete",
        "lojas_marketplace",
        "formato_frete IN ('sem_frete','gratis','taxa_fixa','plataforma')",
    )

    # 2. Pedido: rastreabilidade de frete
    op.add_column("pedidos_marketplace", sa.Column("formato_frete_snapshot", sa.String(20), nullable=True))
    op.add_column("pedidos_marketplace", sa.Column("custo_frete", sa.Numeric(10, 2), nullable=True))
    op.add_column("pedidos_marketplace", sa.Column("lucro_frete", sa.Numeric(10, 2), nullable=True))

    # 3. Extrato: frete cobrado do cliente
    op.add_column("extrato_loja", sa.Column("valor_frete_cliente", sa.Numeric(10, 2), nullable=True))

    # 4. Repasse: separação produto vs frete
    op.add_column("repasses", sa.Column("valor_bruto_produto", sa.Numeric(12, 2), nullable=True))
    op.add_column("repasses", sa.Column("valor_bruto_frete", sa.Numeric(12, 2), nullable=True))

    # 5. Entregador: N veículos com capacidade
    op.create_table(
        "entregador_veiculos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entregador_id", sa.Integer(), sa.ForeignKey("entregadores.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tipo_veiculo", sa.String(20), nullable=True),
        sa.Column("capacidade_kg", sa.Numeric(10, 2), nullable=True),
        sa.Column("descricao", sa.String(100), nullable=True),
        sa.Column("placa", sa.String(10), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("entregador_id", "placa", name="uq_entregador_placa"),
    )


def downgrade() -> None:
    op.drop_table("entregador_veiculos")
    op.drop_column("repasses", "valor_bruto_frete")
    op.drop_column("repasses", "valor_bruto_produto")
    op.drop_column("extrato_loja", "valor_frete_cliente")
    op.drop_column("pedidos_marketplace", "lucro_frete")
    op.drop_column("pedidos_marketplace", "custo_frete")
    op.drop_column("pedidos_marketplace", "formato_frete_snapshot")
    op.drop_constraint("ck_loja_formato_frete", "lojas_marketplace", type_="check")
    op.drop_column("lojas_marketplace", "formato_frete")
