"""Multi-brand Fase 3.1: backfill consumidor órfãos + reconciliação módulos canônicos.

Revision ID: br32_consumidor_modules
Revises: br31_tenant_brand_id_slug
Create Date: 2026-06-18
"""
import sqlalchemy as sa
from alembic import op

revision = "br32_consumidor_modules"
down_revision = "br31_tenant_brand_id_slug"
branch_labels = None
depends_on = None

CANONICAL_MODULES = (
    ("Core PDV", "core", "Gestão do negócio (PDV, estoque, fiscal)"),
    ("Marketplace", "marketplace", "Vitrine e vendas online"),
    ("Certificados", "certificados", "Emissão de certificados (Certipeso — futuro)"),
    ("Calibração", "calibracao", "Calibração (Certipeso — futuro)"),
)


def upgrade() -> None:
    conn = op.get_bind()

    for nome, slug, descricao in CANONICAL_MODULES:
        conn.execute(
            sa.text(
                """
                INSERT INTO modules (nome, slug, descricao, ativo, created_at, updated_at)
                VALUES (:nome, :slug, :descricao, true, NOW(), NOW())
                ON CONFLICT (slug) DO NOTHING
                """
            ),
            {"nome": nome, "slug": slug, "descricao": descricao},
        )

    conn.execute(
        sa.text(
            """
            UPDATE consumidores_marketplace c
            SET tenant_id = sub.cliente_id
            FROM (
                SELECT DISTINCT ON (p.comprador_id)
                    p.comprador_id,
                    l.cliente_id
                FROM pedidos_marketplace p
                JOIN lojas_marketplace l ON l.id = p.loja_id
                WHERE p.comprador_id IS NOT NULL
                ORDER BY p.comprador_id, p.created_at ASC
            ) sub
            WHERE c.id = sub.comprador_id
              AND c.tenant_id IS NULL
              AND c.deleted_at IS NULL
            """
        )
    )

    conn.execute(
        sa.text(
            """
            UPDATE enderecos_consumidor e
            SET tenant_id = c.tenant_id
            FROM consumidores_marketplace c
            WHERE e.consumidor_id = c.id
              AND e.tenant_id IS NULL
              AND c.tenant_id IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    pass
