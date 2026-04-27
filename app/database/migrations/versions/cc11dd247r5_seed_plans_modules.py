"""seed plans and modules (SaaS catálogo inicial)

Revision ID: cc11dd247r5
Revises: bb00cc136q4
Create Date: 2026-02-08

Insere planos e módulos iniciais para UI de assinatura.
"""
import sqlalchemy as sa
from alembic import op

revision = "cc11dd247r5"
down_revision = "bb00cc136q4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO plans (nome, slug, descricao, preco, ativo) VALUES "
            "('Básico', 'basico', 'Plano básico', 99.00, true), "
            "('Profissional', 'profissional', 'Plano profissional', 199.00, true), "
            "('Empresarial', 'empresarial', 'Plano empresarial', 399.00, true)"
        )
    )
    conn.execute(
        sa.text(
            "INSERT INTO modules (nome, slug, descricao, ativo) VALUES "
            "('Certificados', 'certificados', 'Emissão e gestão de certificados', true), "
            "('Fiscal', 'fiscal', 'Notas fiscais e faturamento', true), "
            "('Qualidade', 'qualidade', 'Qualidade ISO 17025', true), "
            "('Clientes e Equipamentos', 'clientes-equipamentos', 'Cadastros e equipamentos', true)"
        )
    )


def downgrade() -> None:
    op.execute("DELETE FROM modules WHERE slug IN ('certificados', 'fiscal', 'qualidade', 'clientes-equipamentos')")
    op.execute("DELETE FROM plans WHERE slug IN ('basico', 'profissional', 'empresarial')")
