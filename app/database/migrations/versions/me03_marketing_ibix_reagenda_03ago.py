"""Marketing Ibix: reagendar campanha 40d (+7 dias; início 03/08/2026).

Calendário anterior (27/07→04/09) não foi executado. Novo: Dia 1 = 03/08/2026,
publicação final = 11/09/2026. Idempotente: só aplica se data_inicio ainda for 2026-07-27.

Revision ID: me03_marketing_ibix_reagenda
Revises: me02_marketing_ibix_editorial
Create Date: 2026-08-02
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "me03_marketing_ibix_reagenda"
down_revision = "me02_marketing_ibix_editorial"
branch_labels = None
depends_on = None

_SLUG = "ibix_market_40d"
_DATA_INICIO_ANTIGA = "2026-07-27"
_DATA_INICIO_NOVA = "2026-08-03"
_DATA_FIM_NOVA = "2026-09-11"
_PROXIMO_PASSO = (
    "Pré-início 02/08: montar posts 1–3 · Postagens a partir de 03/08/2026 "
    "· Aprovar copies 2–7 → Bloco B"
)

# numero → nova data_prevista (ritmo meio-termo, +7 dias)
_POSTS_DATAS = [
    (1, "2026-08-03"),
    (2, "2026-08-05"),
    (3, "2026-08-07"),
    (4, "2026-08-08"),
    (5, "2026-08-09"),
    (6, "2026-08-10"),
    (7, "2026-08-12"),
    (8, "2026-08-14"),
    (9, "2026-08-15"),
    (10, "2026-08-16"),
    (11, "2026-08-17"),
    (12, "2026-08-19"),
    (13, "2026-08-21"),
    (14, "2026-08-22"),
    (15, "2026-08-23"),
    (16, "2026-08-24"),
    (17, "2026-08-26"),
    (18, "2026-08-28"),
    (19, "2026-08-29"),
    (20, "2026-08-30"),
    (21, "2026-08-31"),
    (22, "2026-09-02"),
    (23, "2026-09-04"),
    (24, "2026-09-05"),
    (25, "2026-09-06"),
    (26, "2026-09-07"),
    (27, "2026-09-09"),
    (28, "2026-09-11"),
]


def upgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(
        text(
            "SELECT id, data_inicio::text FROM marketing_campanhas WHERE slug = :slug"
        ),
        {"slug": _SLUG},
    ).fetchone()
    if not row:
        return
    campanha_id, data_inicio = int(row[0]), str(row[1])[:10]
    if data_inicio != _DATA_INICIO_ANTIGA:
        return

    conn.execute(
        text(
            """
            UPDATE marketing_campanhas
            SET data_inicio = :di,
                data_fim = :df,
                proximo_passo = :passo,
                updated_at = NOW()
            WHERE id = :cid
            """
        ),
        {
            "di": _DATA_INICIO_NOVA,
            "df": _DATA_FIM_NOVA,
            "passo": _PROXIMO_PASSO,
            "cid": campanha_id,
        },
    )
    for numero, data_prevista in _POSTS_DATAS:
        conn.execute(
            text(
                """
                UPDATE marketing_posts
                SET data_prevista = :dp, updated_at = NOW()
                WHERE campanha_id = :cid AND numero = :numero
                """
            ),
            {"dp": data_prevista, "cid": campanha_id, "numero": numero},
        )


def downgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(
        text(
            "SELECT id, data_inicio::text FROM marketing_campanhas WHERE slug = :slug"
        ),
        {"slug": _SLUG},
    ).fetchone()
    if not row:
        return
    campanha_id, data_inicio = int(row[0]), str(row[1])[:10]
    if data_inicio != _DATA_INICIO_NOVA:
        return

    conn.execute(
        text(
            """
            UPDATE marketing_campanhas
            SET data_inicio = '2026-07-27',
                data_fim = '2026-09-04',
                proximo_passo = 'Aprovar copies 2–7 (Bloco A) → Bloco B',
                updated_at = NOW()
            WHERE id = :cid
            """
        ),
        {"cid": campanha_id},
    )
    # Reverte +7 dias em todos os posts da campanha
    conn.execute(
        text(
            """
            UPDATE marketing_posts
            SET data_prevista = data_prevista - INTERVAL '7 days',
                updated_at = NOW()
            WHERE campanha_id = :cid
            """
        ),
        {"cid": campanha_id},
    )
