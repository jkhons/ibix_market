"""Marketing Ibix Lançamento: campanha + 28 posts operacionais.

Revision ID: me01_marketing_ibix_lancamento
Revises: rb01_cleanup_permissoes_certipeso
Create Date: 2026-07-31
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "me01_marketing_ibix_lancamento"
down_revision = "rb01_cleanup_permissoes_certipeso"
branch_labels = None
depends_on = None

# Fonte: MARKETING_ESTRUTURADO/calendario_40_dias.md (tipo B–D por dia da semana).
_POSTS = [
    # numero, data, bloco, tipo, tema, angulo, copy_ref, status_copy
    (1, "2026-07-27", "A", "cheio", "O que é / gancho curiosidade", "Objetivo", "copies_bloco_a.md#post-1", "aprovado"),
    (2, "2026-07-29", "A", "cheio", "Foco inicial: Lençóis Paulista", "Objetivo / local", "copies_bloco_a.md#post-2", "proposta"),
    (3, "2026-07-31", "A", "cheio", "Estamos finalizando / construindo", "Bastidores", "copies_bloco_a.md#post-3", "proposta"),
    (4, "2026-08-01", "A", "leve", "Vitrine: lojas locais em um só lugar", "Objetivo", "copies_bloco_a.md#post-4", "proposta"),
    (5, "2026-08-02", "A", "reuso", "Melhor da semana (provável #1 ou #4)", "Reforço", "copies_bloco_a.md#post-5", "proposta"),
    (6, "2026-08-03", "A", "cheio", "Tela: publicar produto / anúncio", "Bastidores", "copies_bloco_a.md#post-6", "proposta"),
    (7, "2026-08-05", "A", "cheio", "Por que marketplace local", "Objetivo", "copies_bloco_a.md#post-7", "proposta"),
    (8, "2026-08-07", "B", "cheio", "Lojista: vender online sem abandonar a loja física", "Lojista", None, "proposta"),
    (9, "2026-08-08", "B", "leve", "Pedidos organizados em um fluxo", "Lojista", None, "proposta"),
    (10, "2026-08-09", "B", "reuso", "Sua loja visível para quem busca na cidade", "Lojista", None, "proposta"),
    (11, "2026-08-10", "B", "cheio", "Tela: Minha loja / anúncios (bastidor)", "Bastidores + lojista", None, "proposta"),
    (12, "2026-08-12", "B", "cheio", "Estoque alinhado à vitrine", "Lojista", None, "proposta"),
    (13, "2026-08-14", "B", "cheio", "Entrega local: você vende, a cidade recebe", "Lojista", None, "proposta"),
    (14, "2026-08-15", "B", "leve", "Feito para comércio de Lençóis Paulista", "Lojista / local", None, "proposta"),
    (15, "2026-08-16", "B", "reuso", "Menos improviso no WhatsApp, mais pedido organizado", "Lojista", None, "proposta"),
    (16, "2026-08-17", "B", "cheio", "Convite soft: lojista interessado → acompanhar / falar conosco", "Lojista + CTA leve", None, "proposta"),
    (17, "2026-08-19", "C", "cheio", "Comprar de lojas da cidade, em um só lugar", "Consumidor", None, "proposta"),
    (18, "2026-08-21", "C", "cheio", "Entrega no mesmo dia", "Entrega", None, "proposta"),
    (19, "2026-08-22", "C", "leve", "Em cerca de duas horas ou agendar", "Entrega", None, "proposta"),
    (20, "2026-08-23", "C", "reuso", "Retirada na loja também (quando a loja oferecer)", "Consumidor / entrega", None, "proposta"),
    (21, "2026-08-24", "C", "cheio", "Tela: produto / carrinho / checkout (bastidor)", "Bastidores + consumidor", None, "proposta"),
    (22, "2026-08-26", "C", "cheio", "Apoiar o comércio local de Lençóis Paulista", "Consumidor / local", None, "proposta"),
    (23, "2026-08-28", "C", "cheio", "Simples: escolhe, pede, recebe na cidade", "Consumidor", None, "proposta"),
    (24, "2026-08-29", "D", "leve", "Contagem: estamos perto da publicação", "Aceleração", None, "proposta"),
    (25, "2026-08-30", "D", "reuso", "Recap curto: o que é + para quem", "Objetivo", None, "proposta"),
    (26, "2026-08-31", "D", "cheio", "Lojista: prepare-se / acompanhe @ibixmarket", "CTA lojista", None, "proposta"),
    (27, "2026-09-02", "D", "cheio", "Consumidor: em breve, lojas da cidade aqui", "CTA consumidor", None, "proposta"),
    (28, "2026-09-04", "D", "cheio", "Publicação final", "Lançamento", None, "proposta"),
]


def upgrade() -> None:
    op.create_table(
        "marketing_campanhas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column("canais", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ativa"),
        sa.Column("proximo_passo", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('ativa', 'encerrada')", name="ck_marketing_campanhas_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_marketing_campanhas_slug"),
    )

    op.create_table(
        "marketing_posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campanha_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("data_prevista", sa.Date(), nullable=False),
        sa.Column("bloco", sa.String(length=1), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("tema", sa.Text(), nullable=False),
        sa.Column("angulo", sa.Text(), nullable=False),
        sa.Column("copy_ref", sa.String(length=200), nullable=True),
        sa.Column("status_copy", sa.String(length=20), nullable=False, server_default="proposta"),
        sa.Column("telas_ok", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status_producao", sa.String(length=20), nullable=False, server_default="pendente"),
        sa.Column("status_publicacao", sa.String(length=20), nullable=False, server_default="pendente"),
        sa.Column("publicado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chk_texto_curto", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("chk_tela_real", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("chk_mesmo_ig_fb", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("chk_frase_ancora", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("chk_entrega_regra", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("chk_stories_mesmo_dia", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reuso_origem_numero", sa.Integer(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("bloco IN ('A', 'B', 'C', 'D')", name="ck_marketing_posts_bloco"),
        sa.CheckConstraint("tipo IN ('cheio', 'leve', 'reuso')", name="ck_marketing_posts_tipo"),
        sa.CheckConstraint(
            "status_copy IN ('proposta', 'aprovado', 'rejeitado')",
            name="ck_marketing_posts_status_copy",
        ),
        sa.CheckConstraint(
            "status_producao IN ('pendente', 'gravado', 'pronto')",
            name="ck_marketing_posts_status_producao",
        ),
        sa.CheckConstraint(
            "status_publicacao IN ('pendente', 'ig', 'fb', 'ambos')",
            name="ck_marketing_posts_status_publicacao",
        ),
        sa.ForeignKeyConstraint(["campanha_id"], ["marketing_campanhas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campanha_id", "numero", name="uq_marketing_posts_campanha_numero"),
    )
    op.create_index(
        "ix_marketing_posts_campanha_data",
        "marketing_posts",
        ["campanha_id", "data_prevista"],
    )

    conn = op.get_bind()
    existing = conn.execute(
        text("SELECT id FROM marketing_campanhas WHERE slug = :slug"),
        {"slug": "ibix_market_40d"},
    ).fetchone()
    if existing:
        campanha_id = existing[0]
    else:
        result = conn.execute(
            text(
                """
                INSERT INTO marketing_campanhas (
                    slug, titulo, data_inicio, data_fim, canais, status, proximo_passo
                ) VALUES (
                    :slug, :titulo, :data_inicio, :data_fim, :canais, :status, :proximo_passo
                ) RETURNING id
                """
            ),
            {
                "slug": "ibix_market_40d",
                "titulo": "Ibix Market — Lançamento 40 dias",
                "data_inicio": "2026-07-27",
                "data_fim": "2026-09-04",
                "canais": "Instagram @ibixmarket · Facebook Ibix Market (mesmo conteúdo)",
                "status": "ativa",
                "proximo_passo": "Aprovar copies 2–7 (Bloco A) → Bloco B",
            },
        )
        campanha_id = result.fetchone()[0]

    count = conn.execute(
        text("SELECT COUNT(*) FROM marketing_posts WHERE campanha_id = :cid"),
        {"cid": campanha_id},
    ).scalar()
    if count and int(count) > 0:
        return

    for numero, data, bloco, tipo, tema, angulo, copy_ref, status_copy in _POSTS:
        conn.execute(
            text(
                """
                INSERT INTO marketing_posts (
                    campanha_id, numero, data_prevista, bloco, tipo, tema, angulo,
                    copy_ref, status_copy, telas_ok, status_producao, status_publicacao
                ) VALUES (
                    :campanha_id, :numero, :data_prevista, :bloco, :tipo, :tema, :angulo,
                    :copy_ref, :status_copy, false, 'pendente', 'pendente'
                )
                """
            ),
            {
                "campanha_id": campanha_id,
                "numero": numero,
                "data_prevista": data,
                "bloco": bloco,
                "tipo": tipo,
                "tema": tema,
                "angulo": angulo,
                "copy_ref": copy_ref,
                "status_copy": status_copy,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_marketing_posts_campanha_data", table_name="marketing_posts")
    op.drop_table("marketing_posts")
    op.drop_table("marketing_campanhas")
