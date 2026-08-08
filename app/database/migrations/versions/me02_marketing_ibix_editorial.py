"""Marketing Ibix Lançamento: conteúdo editorial operacional no UI (copies + guia).

Revision ID: me02_marketing_ibix_editorial
Revises: me01_marketing_ibix_lancamento
Create Date: 2026-07-31
"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

revision = "me02_marketing_ibix_editorial"
down_revision = "me01_marketing_ibix_lancamento"
branch_labels = None
depends_on = None

# Fonte: MARKETING_ESTRUTURADO/plano.md + copies_bloco_a.md (sem inventar B–D).
_COPIES = {
    1: {
        "duracao": "12–16s · 4 cortes",
        "legenda_reels": "E se as lojas de Lençóis estivessem todas em um só lugar?\nIbix Market · Em breve",
        "roteiro_notas": None,
        "telas_necessarias": "Celular/marca · vitrine · logo",
        "cortes": [
            {"corte": 1, "tempo": "0–3s", "texto_tela": "E se as lojas de Lençóis estivessem todas em um só lugar?", "visual": "Celular / marca"},
            {"corte": 2, "tempo": "3–7s", "texto_tela": "Lojas daqui. Num só lugar.", "visual": "Vitrine"},
            {"corte": 3, "tempo": "7–12s", "texto_tela": "Lençóis Paulista", "visual": "Cidade + UI ou tipografia"},
            {"corte": 4, "tempo": "12–16s", "texto_tela": "Ibix Market · Em breve", "visual": "Logo / home"},
        ],
    },
    2: {
        "duracao": "10–14s · 4 cortes",
        "legenda_reels": "Começamos onde a gente vive.\nIbix Market · Lençóis Paulista",
        "roteiro_notas": None,
        "telas_necessarias": "Cidade · vitrine · logo",
        "cortes": [
            {"corte": 1, "tempo": "0–3s", "texto_tela": "Começamos em casa.", "visual": "Marca / abertura rápida"},
            {"corte": 2, "tempo": "3–6s", "texto_tela": "Lençóis Paulista — SP", "visual": "Cidade / detalhe local"},
            {"corte": 3, "tempo": "6–10s", "texto_tela": "Lojas da cidade. Entrega por aqui.", "visual": "Vitrine ou mapa mental da cidade na UI"},
            {"corte": 4, "tempo": "10–13s", "texto_tela": "Ibix Market", "visual": "Logo · soft"},
        ],
    },
    3: {
        "duracao": "10–14s · 4 cortes",
        "legenda_reels": "Nos bastidores: finalizando o marketplace local.\nEm breve · Lençóis Paulista",
        "roteiro_notas": None,
        "telas_necessarias": "Bastidor painel · logo",
        "cortes": [
            {"corte": 1, "tempo": "0–3s", "texto_tela": "Ainda não abriu.", "visual": "Tela / cursor / bastidor"},
            {"corte": 2, "tempo": "3–7s", "texto_tela": "Mas já está quase.", "visual": "Painel lojista ou anúncio"},
            {"corte": 3, "tempo": "7–11s", "texto_tela": "Construindo pra Lençóis Paulista.", "visual": "UI real + tipografia"},
            {"corte": 4, "tempo": "11–14s", "texto_tela": "Ibix Market · Em breve", "visual": "Logo"},
        ],
    },
    4: {
        "duracao": "6–10s · 2–3 cortes",
        "legenda_reels": "Várias lojas. Um só lugar.\nA vitrine local está chegando.",
        "roteiro_notas": None,
        "telas_necessarias": "Vitrine scroll · home · logo",
        "cortes": [
            {"corte": 1, "tempo": "0–3s", "texto_tela": "Cansou de caçar loja por loja?", "visual": "Gancho"},
            {"corte": 2, "tempo": "3–7s", "texto_tela": "Várias lojas. Um só lugar.", "visual": "Scroll vitrine / home"},
            {"corte": 3, "tempo": "7–9s", "texto_tela": "Ibix Market · Em breve", "visual": "Logo (opcional se já couber no 2)"},
        ],
    },
    5: {
        "duracao": "5–8s (recorte) · Stories; Reels opcional",
        "legenda_reels": "Se perdeu: estamos chegando em Lençóis Paulista.\nIbix Market",
        "roteiro_notas": (
            "Não gravar roteiro novo. Repetir o melhor da semana (Stories; Reels opcional). "
            "Preferência inicial: Post 1 (gancho forte) ou Post 4 (se performar melhor). "
            "Pode ser só recorte de 5–8s + sticker «Em breve»."
        ),
        "telas_necessarias": "Reuso do material da semana (Post 1 ou 4)",
        "cortes": [],
    },
    6: {
        "duracao": "10–14s · 4 cortes",
        "legenda_reels": "Bastidores: o lojista publica. A cidade vê.",
        "roteiro_notas": None,
        "telas_necessarias": "Publicar anúncio · mesmo item na vitrine · logo",
        "cortes": [
            {"corte": 1, "tempo": "0–3s", "texto_tela": "Nos bastidores.", "visual": "Painel"},
            {"corte": 2, "tempo": "3–7s", "texto_tela": "Lojista publica o produto.", "visual": "Criar/editar anúncio"},
            {"corte": 3, "tempo": "7–11s", "texto_tela": "A cidade vê na vitrine.", "visual": "Mesmo produto na vitrine"},
            {"corte": 4, "tempo": "11–14s", "texto_tela": "Ibix Market · Em breve", "visual": "Logo"},
        ],
    },
    7: {
        "duracao": "10–14s · 4 cortes",
        "legenda_reels": "Não é mais um app genérico.\nÉ Lençóis Paulista.",
        "roteiro_notas": "Prazo «mesmo dia / 2h» fica para o Bloco C — aqui só «entrega curta».",
        "telas_necessarias": "Tipografia · vitrine/cidade · logo",
        "cortes": [
            {"corte": 1, "tempo": "0–3s", "texto_tela": "Não é marketplace genérico.", "visual": "Tipografia forte"},
            {"corte": 2, "tempo": "3–7s", "texto_tela": "É local.", "visual": "Vitrine / cidade"},
            {"corte": 3, "tempo": "7–11s", "texto_tela": "Lençóis Paulista.", "visual": "Nome da cidade grande"},
            {"corte": 4, "tempo": "11–14s", "texto_tela": "Venda + entrega curta. · Ibix Market", "visual": "Logo · Em breve"},
        ],
    },
}


def upgrade() -> None:
    op.add_column("marketing_campanhas", sa.Column("formato", sa.Text(), nullable=True))
    op.add_column("marketing_campanhas", sa.Column("tom", sa.Text(), nullable=True))
    op.add_column("marketing_campanhas", sa.Column("linha_gancho", sa.String(length=80), nullable=True))
    op.add_column("marketing_campanhas", sa.Column("frase_ancora", sa.Text(), nullable=True))
    op.add_column("marketing_campanhas", sa.Column("linha_editorial", sa.Text(), nullable=True))
    op.add_column("marketing_campanhas", sa.Column("ritmo_resumo", sa.Text(), nullable=True))
    op.add_column("marketing_campanhas", sa.Column("politica_reuso", sa.Text(), nullable=True))

    op.add_column("marketing_posts", sa.Column("duracao", sa.String(length=120), nullable=True))
    op.add_column("marketing_posts", sa.Column("legenda_reels", sa.Text(), nullable=True))
    op.add_column("marketing_posts", sa.Column("roteiro_notas", sa.Text(), nullable=True))
    op.add_column("marketing_posts", sa.Column("telas_necessarias", sa.Text(), nullable=True))
    op.add_column("marketing_posts", sa.Column("cortes", JSONB(), nullable=True))

    conn = op.get_bind()
    conn.execute(
        text(
            """
            UPDATE marketing_campanhas SET
              formato = :formato,
              tom = :tom,
              linha_gancho = :linha_gancho,
              frase_ancora = :frase_ancora,
              linha_editorial = :linha_editorial,
              ritmo_resumo = :ritmo_resumo,
              politica_reuso = :politica_reuso
            WHERE slug = 'ibix_market_40d'
            """
        ),
        {
            "formato": "Stories / Reels · vertical 9:16 · texto grande · cortes rápidos",
            "tom": "Ritmo Americanas (gancho → benefício → corte rápido → CTA) — sem copiar visual/cores",
            "linha_gancho": "B — curiosidade",
            "frase_ancora": (
                "Marketplace que organiza a venda de lojistas locais e a entrega local com prazo curto. "
                "Inicialmente focado em Lençóis Paulista."
            ),
            "linha_editorial": (
                "1) Objetivo da ferramenta · 2) Benefício do lojista (Lençóis Paulista) · "
                "3) Benefício do consumidor"
            ),
            "ritmo_resumo": (
                "Presença Seg, Qua, Sex, Sáb, Dom. Cheio (4 cortes + Stories) Seg/Qua/Sex. "
                "Leve Sáb (2–3 cortes). Reuso Dom (melhor da semana)."
            ),
            "politica_reuso": (
                "Pode: Stories no mesmo dia do Reels; domingo republicar/recortar o melhor da semana; "
                "após 10–14 dias repetir ganhador com legenda nova. "
                "Não: mesmo Reels no feed no dia seguinte; fingir conteúdo novo sem recorte/legenda."
            ),
        },
    )

    campanha = conn.execute(
        text("SELECT id FROM marketing_campanhas WHERE slug = 'ibix_market_40d'")
    ).fetchone()
    if not campanha:
        return
    campanha_id = campanha[0]

    for numero, data in _COPIES.items():
        conn.execute(
            text(
                """
                UPDATE marketing_posts SET
                  duracao = :duracao,
                  legenda_reels = :legenda_reels,
                  roteiro_notas = :roteiro_notas,
                  telas_necessarias = :telas_necessarias,
                  cortes = CAST(:cortes AS jsonb)
                WHERE campanha_id = :campanha_id AND numero = :numero
                """
            ),
            {
                "campanha_id": campanha_id,
                "numero": numero,
                "duracao": data["duracao"],
                "legenda_reels": data["legenda_reels"],
                "roteiro_notas": data["roteiro_notas"],
                "telas_necessarias": data["telas_necessarias"],
                "cortes": json.dumps(data["cortes"], ensure_ascii=False),
            },
        )


def downgrade() -> None:
    op.drop_column("marketing_posts", "cortes")
    op.drop_column("marketing_posts", "telas_necessarias")
    op.drop_column("marketing_posts", "roteiro_notas")
    op.drop_column("marketing_posts", "legenda_reels")
    op.drop_column("marketing_posts", "duracao")
    op.drop_column("marketing_campanhas", "politica_reuso")
    op.drop_column("marketing_campanhas", "ritmo_resumo")
    op.drop_column("marketing_campanhas", "linha_editorial")
    op.drop_column("marketing_campanhas", "frase_ancora")
    op.drop_column("marketing_campanhas", "linha_gancho")
    op.drop_column("marketing_campanhas", "tom")
    op.drop_column("marketing_campanhas", "formato")
