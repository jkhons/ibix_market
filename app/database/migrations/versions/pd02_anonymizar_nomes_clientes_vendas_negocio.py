"""Anonimiza nomes de clientes em vendas (tela Negócio > Venda — vendas realizadas).

Revision ID: pd02_anonymizar_nomes_clientes_vendas_negocio
Revises: pd01_anonymizar_nomes_pedidos_negocio_marketplace
Create Date: 2026-05-04

A listagem em GET /api/v1/vendas faz JOIN em clientes.nome. Esta migration altera clientes.nome
apenas para cliente_id que aparecem em vendas, excluindo IDs reconhecidos como estabelecimento
(empresa fiscal, tenant CA, loja marketplace, catálogo produtos_cliente, estabelecimento fiscal).

Downgrade não restaura os valores originais.
"""
from __future__ import annotations

import secrets

from alembic import op
from sqlalchemy import text

revision = "pd02_anonymizar_nomes_clientes_vendas_negocio"
down_revision = "pd01_anonymizar_nomes_pedidos_negocio_marketplace"
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


def _coletar_ids_estabelecimento(conn) -> set[int]:
    """IDs de clientes que representam loja/CA/emissor — não anonimizar."""
    excluir: set[int] = set()
    queries = [
        "SELECT DISTINCT cliente_id AS cid FROM empresa WHERE cliente_id IS NOT NULL",
        "SELECT DISTINCT ca_cliente_id AS cid FROM tenants WHERE ca_cliente_id IS NOT NULL",
        "SELECT DISTINCT cliente_id AS cid FROM lojas_marketplace WHERE cliente_id IS NOT NULL",
        "SELECT DISTINCT cliente_id AS cid FROM estabelecimentos_fiscais",
        "SELECT DISTINCT cliente_id AS cid FROM produtos_cliente",
    ]
    for q in queries:
        for row in conn.execute(text(q)).fetchall():
            v = row[0]
            if v is not None:
                excluir.add(int(v))
    return excluir


def upgrade() -> None:
    conn = op.get_bind()
    rng = secrets.SystemRandom()
    excluir = _coletar_ids_estabelecimento(conn)

    r = conn.execute(
        text("SELECT DISTINCT cliente_id FROM vendas WHERE cliente_id IS NOT NULL")
    )
    alvo: set[int] = set()
    for row in r.fetchall():
        cid = row[0]
        if cid is not None and int(cid) not in excluir:
            alvo.add(int(cid))

    for cid in sorted(alvo):
        novo = _nome_aleatorio(rng)[:255]
        conn.execute(
            text("UPDATE clientes SET nome = :nome WHERE id = :id"),
            {"nome": novo, "id": cid},
        )


def downgrade() -> None:
    pass
