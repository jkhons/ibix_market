"""Multi-brand: tabelas brands + brand_domains e seed Ibix (origem) + Solumática.

Revision ID: br01_multibrand_brands_domains
Revises: pl01_platform_novo_ca_notificacoes
Create Date: 2026-06-18
"""
import sqlalchemy as sa
from alembic import op

revision = "br01_multibrand_brands_domains"
down_revision = "pl01_platform_novo_ca_notificacoes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("nome_exibicao", sa.String(length=255), nullable=False),
        sa.Column("nome_curto", sa.String(length=80), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=False),
        sa.Column("logo_footer_url", sa.String(length=500), nullable=True),
        sa.Column("favicon_url", sa.String(length=500), nullable=True),
        sa.Column("telefone", sa.String(length=30), nullable=True),
        sa.Column("whatsapp", sa.String(length=30), nullable=True),
        sa.Column("email_remetente", sa.String(length=255), nullable=True),
        sa.Column("cor_primaria", sa.String(length=20), nullable=True),
        sa.Column("cor_secundaria", sa.String(length=20), nullable=True),
        sa.Column("seo_base_url", sa.String(length=500), nullable=True),
        sa.Column("is_origem", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_brands_slug"),
        comment="Marcas white-label (Ibix origem, Solumática, etc.)",
    )
    op.create_index("ix_brands_ativo", "brands", ["ativo"], unique=False)
    op.create_index("ix_brands_is_origem", "brands", ["is_origem"], unique=False)

    op.create_table(
        "brand_domains",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("dominio", sa.String(length=255), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dominio", name="uq_brand_domains_dominio"),
        comment="Mapeamento domínio → marca",
    )
    op.create_index("ix_brand_domains_brand_id", "brand_domains", ["brand_id"], unique=False)
    op.create_index("ix_brand_domains_brand_ativo", "brand_domains", ["brand_id", "ativo"], unique=False)

    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            INSERT INTO brands (
                slug, nome_exibicao, nome_curto, logo_url, logo_footer_url, favicon_url,
                telefone, whatsapp, email_remetente, cor_primaria, cor_secundaria,
                seo_base_url, is_origem, ativo, created_at, updated_at
            ) VALUES (
                'ibix', 'PDV Ibix', 'Ibix',
                '/static/img/ibix/cab.png', '/static/img/ibix/rodape.png', '/static/img/arte-pdv.png',
                NULL, NULL, NULL, '#C47A44', '#2F3A44',
                'https://www.ibix.com.br', true, true, NOW(), NOW()
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO brands (
                slug, nome_exibicao, nome_curto, logo_url, logo_footer_url, favicon_url,
                telefone, whatsapp, email_remetente, cor_primaria, cor_secundaria,
                seo_base_url, is_origem, ativo, created_at, updated_at
            ) VALUES (
                'solumatica', 'PDV Solumática', 'Solumática',
                '/static/img/solumatica/cab.png', '/static/img/solumatica/rodape.png', '/static/img/arte-pdv.png',
                NULL, NULL, NULL, '#2c3e50', '#34495e',
                'https://www.solumatica.com.br', false, true, NOW(), NOW()
            )
            """
        )
    )

    ibix_id = conn.execute(sa.text("SELECT id FROM brands WHERE slug = 'ibix'")).scalar()
    sol_id = conn.execute(sa.text("SELECT id FROM brands WHERE slug = 'solumatica'")).scalar()

    ibix_domains = (
        "www.ibix.com.br",
        "ibix.com.br",
        "auto.ibix.com.br",
        "localhost",
        "127.0.0.1",
    )
    sol_domains = (
        "www.solumatica.com.br",
        "solumatica.com.br",
        "auto.solumatica.com.br",
    )
    for dom in ibix_domains:
        conn.execute(
            sa.text(
                "INSERT INTO brand_domains (brand_id, dominio, ativo, created_at, updated_at) "
                "VALUES (:bid, :dom, true, NOW(), NOW())"
            ),
            {"bid": ibix_id, "dom": dom},
        )
    for dom in sol_domains:
        conn.execute(
            sa.text(
                "INSERT INTO brand_domains (brand_id, dominio, ativo, created_at, updated_at) "
                "VALUES (:bid, :dom, true, NOW(), NOW())"
            ),
            {"bid": sol_id, "dom": dom},
        )


def downgrade() -> None:
    op.drop_index("ix_brand_domains_brand_ativo", table_name="brand_domains")
    op.drop_index("ix_brand_domains_brand_id", table_name="brand_domains")
    op.drop_table("brand_domains")
    op.drop_index("ix_brands_is_origem", table_name="brands")
    op.drop_index("ix_brands_ativo", table_name="brands")
    op.drop_table("brands")
