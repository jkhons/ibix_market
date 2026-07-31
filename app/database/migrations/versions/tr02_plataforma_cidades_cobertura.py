"""Cidades/regiões atendidas pela plataforma marketplace (lista única definida pelo Superadmin).

Somente quando existir pelo menos uma linha ativa a entrega ao domicilio exige
cidade + UF dentro desta lista (checkout + regra de áreas por loja).

Revision ID: tr02_plataforma_cidades
Revises: rm01_remove_usuarios_demo_mai2026
"""

from alembic import op
import sqlalchemy as sa


revision = "tr02_plataforma_cidades"
down_revision = "rm01_remove_usuarios_demo_mai2026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plataforma_cidades_cobertura",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("cidade", sa.String(length=120), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("codigo_ibge", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_plataforma_cidades_ativo",
        "plataforma_cidades_cobertura",
        ["ativo"],
    )


def downgrade() -> None:
    op.drop_index("ix_plataforma_cidades_ativo", table_name="plataforma_cidades_cobertura")
    op.drop_table("plataforma_cidades_cobertura")
