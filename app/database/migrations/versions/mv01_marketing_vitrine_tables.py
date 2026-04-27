"""Marketing vitrine: config singleton + cards (destaques / oferta_semana).

Revision ID: mv01_marketing_vitrine
Revises: seo03_nf_desc
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "mv01_marketing_vitrine"
down_revision = "seo03_nf_desc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketing_vitrine_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("mostrar_todos_produtos", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("titulo_ofertas_semana", sa.String(length=200), nullable=True),
        sa.Column("subtitulo_ofertas_semana", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_marketing_vitrine_config_singleton"),
        sa.ForeignKeyConstraint(["updated_by"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        INSERT INTO marketing_vitrine_config (id, mostrar_todos_produtos, ativo, created_at, updated_at)
        VALUES (1, true, true, now(), now())
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.create_table(
        "marketing_vitrine_cards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("tipo_bloco", sa.String(length=20), nullable=False),
        sa.Column("tipo_card", sa.String(length=20), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("imagem_url", sa.Text(), nullable=True),
        sa.Column("link_url", sa.Text(), nullable=True),
        sa.Column("anuncio_id", sa.Integer(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("inicio_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fim_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["anuncio_id"], ["anuncios_plataforma.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_vitrine_cards_tipo_bloco", "marketing_vitrine_cards", ["tipo_bloco"])
    op.create_index("ix_marketing_vitrine_cards_anuncio_id", "marketing_vitrine_cards", ["anuncio_id"])


def downgrade() -> None:
    op.drop_index("ix_marketing_vitrine_cards_anuncio_id", table_name="marketing_vitrine_cards")
    op.drop_index("ix_marketing_vitrine_cards_tipo_bloco", table_name="marketing_vitrine_cards")
    op.drop_table("marketing_vitrine_cards")
    op.drop_table("marketing_vitrine_config")
