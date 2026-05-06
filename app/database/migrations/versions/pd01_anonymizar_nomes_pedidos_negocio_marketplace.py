"""Anonimiza nomes de comprador/destinatário em pedidos marketplace (tela Negócio > Pedidos).

Revision ID: pd01_anonymizar_nomes_pedidos_negocio_marketplace
Revises: en02_usuario_notif_backfill_if_missing
Create Date: 2026-05-04

Altera comprador_nome e destinatario_nome em pedidos_marketplace e nome em consumidores_marketplace
ligados por comprador_id, usando nomes aleatórios (anonimização / demo).

Downgrade não restaura os valores originais.
"""
from __future__ import annotations

import secrets

from alembic import op
from sqlalchemy import text

revision = "pd01_anonymizar_nomes_pedidos_negocio_marketplace"
down_revision = "en02_usuario_notif_backfill_if_missing"
branch_labels = None
depends_on = None

_NOMES = (
    "Ana",
    "Beatriz",
    "Carlos",
    "Daniel",
    "Eduardo",
    "Fernanda",
    "Gabriel",
    "Helena",
    "Igor",
    "Juliana",
    "Lucas",
    "Mariana",
    "Nicolas",
    "Olivia",
    "Paulo",
    "Rafael",
    "Sandra",
    "Tiago",
    "Vanessa",
    "Yuri",
)

_SOBRENOMES = (
    "Almeida",
    "Barbosa",
    "Carvalho",
    "Dias",
    "Ferreira",
    "Gomes",
    "Lima",
    "Martins",
    "Monteiro",
    "Nascimento",
    "Oliveira",
    "Pereira",
    "Ribeiro",
    "Rodrigues",
    "Santos",
    "Silva",
    "Souza",
    "Teixeira",
    "Vieira",
    "Xavier",
)


def _nome_aleatorio(rng: secrets.SystemRandom) -> str:
    return f"{rng.choice(_NOMES)} {rng.choice(_SOBRENOMES)}"


def upgrade() -> None:
    conn = op.get_bind()
    rng = secrets.SystemRandom()

    r = conn.execute(
        text(
            "SELECT id, comprador_id, comprador_nome, destinatario_nome "
            "FROM pedidos_marketplace"
        )
    )
    rows = r.fetchall()
    if not rows:
        return

    nome_por_consumidor: dict[int, str] = {}
    for row in rows:
        cid = row.comprador_id
        if cid is not None and cid not in nome_por_consumidor:
            nome_por_consumidor[cid] = _nome_aleatorio(rng)

    for cid, nome in nome_por_consumidor.items():
        conn.execute(
            text("UPDATE consumidores_marketplace SET nome = :nome WHERE id = :id"),
            {"nome": nome[:200], "id": cid},
        )

    for row in rows:
        pid = row.id
        cid = row.comprador_id
        if cid is not None:
            comprador = nome_por_consumidor[cid]
        else:
            comprador = _nome_aleatorio(rng)

        dest = row.destinatario_nome
        if dest is not None and str(dest).strip() != "":
            dest_novo = _nome_aleatorio(rng)[:200]
        else:
            dest_novo = None

        conn.execute(
            text(
                "UPDATE pedidos_marketplace SET comprador_nome = :c, "
                "destinatario_nome = :d WHERE id = :id"
            ),
            {"c": comprador[:200], "d": dest_novo, "id": pid},
        )


def downgrade() -> None:
    pass
