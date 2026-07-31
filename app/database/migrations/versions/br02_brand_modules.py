"""Multi-brand Fase 2: brand_modules + módulos canônicos + seed Ibix/Solumática.

Revision ID: br02_brand_modules
Revises: br01_multibrand_brands_domains
Create Date: 2026-06-18
"""
import sqlalchemy as sa
from alembic import op

revision = "br02_brand_modules"
down_revision = "br01_multibrand_brands_domains"
branch_labels = None
depends_on = None

CANONICAL_MODULES = (
    ("Core PDV", "core", "Gestão do negócio (PDV, estoque, fiscal)"),
    ("Marketplace", "marketplace", "Vitrine e vendas online"),
    ("Certificados", "certificados", "Emissão de certificados (Certipeso — futuro)"),
    ("Calibração", "calibracao", "Calibração (Certipeso — futuro)"),
)


def upgrade() -> None:
    op.create_table(
        "brand_modules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_id", "module_id", name="uq_brand_modules_brand_module"),
        comment="Módulos disponíveis por marca",
    )
    op.create_index("ix_brand_modules_brand_id", "brand_modules", ["brand_id"], unique=False)
    op.create_index("ix_brand_modules_module_id", "brand_modules", ["module_id"], unique=False)

    conn = op.get_bind()

    for nome, slug, descricao in CANONICAL_MODULES:
        conn.execute(
            sa.text(
                """
                INSERT INTO modules (nome, slug, descricao, ativo, created_at, updated_at)
                SELECT :nome, :slug, :descricao, true, NOW(), NOW()
                WHERE NOT EXISTS (SELECT 1 FROM modules WHERE slug = :slug)
                """
            ),
            {"nome": nome, "slug": slug, "descricao": descricao},
        )

    def _link_brand_modules(brand_slug: str, module_slugs: tuple[str, ...]) -> None:
        brand_id = conn.execute(
            sa.text("SELECT id FROM brands WHERE slug = :slug"),
            {"slug": brand_slug},
        ).scalar()
        if not brand_id:
            return
        for mod_slug in module_slugs:
            module_id = conn.execute(
                sa.text("SELECT id FROM modules WHERE slug = :slug"),
                {"slug": mod_slug},
            ).scalar()
            if not module_id:
                continue
            exists = conn.execute(
                sa.text(
                    "SELECT 1 FROM brand_modules WHERE brand_id = :bid AND module_id = :mid"
                ),
                {"bid": brand_id, "mid": module_id},
            ).fetchone()
            if not exists:
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO brand_modules (brand_id, module_id, created_at, updated_at)
                        VALUES (:bid, :mid, NOW(), NOW())
                        """
                    ),
                    {"bid": brand_id, "mid": module_id},
                )

    _link_brand_modules("ibix", ("core", "marketplace"))
    _link_brand_modules("solumatica", ("core",))
    # Certipeso brand ainda não existe — preparar quando entrar na Fase futura


def downgrade() -> None:
    op.drop_index("ix_brand_modules_module_id", table_name="brand_modules")
    op.drop_index("ix_brand_modules_brand_id", table_name="brand_modules")
    op.drop_table("brand_modules")
