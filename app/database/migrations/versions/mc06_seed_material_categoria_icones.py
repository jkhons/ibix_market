"""Seed de ícones para categorias de material.

Revision ID: mc06_seed_material_icones
Revises: mc05_material_icone
Create Date: 2026-03-26
"""
import sqlalchemy as sa
from alembic import op

revision = "mc06_seed_material_icones"
down_revision = "mc05_material_icone"
branch_labels = None
depends_on = None


ICONES_POR_CODIGO = {
    "ALIMENTOS_BEBIDAS": "/static/icones/categorias/alimentos_bebidas.svg",
    "AUTOMOTIVO": "/static/icones/categorias/automotivo.svg",
    "BELEZA_CUIDADOS": "/static/icones/categorias/beleza_cuidados.svg",
    "BRINQUEDOS_JOGOS": "/static/icones/categorias/brinquedos_jogos.svg",
    "CASA_JARDIM_LIMPEZA": "/static/icones/categorias/casa_jardim_limpeza.svg",
    "ELETRONICOS": "/static/icones/categorias/eletronicos.svg",
    "FERRAMENTAS": "/static/icones/categorias/ferramentas.svg",
    "ROUPAS_CALCADOS": "/static/icones/categorias/roupas_calcados.svg",
    "BEBES": "/static/icones/categorias/bebes.svg",
    "COZINHA": "/static/icones/categorias/cozinha.svg",
    "ESPORTES_FITNESS": "/static/icones/categorias/esportes_fitness.svg",
    "GAMES_CONSOLES": "/static/icones/categorias/games_consoles.svg",
    "LIVROS_PAPELARIA": "/static/icones/categorias/livros_papelaria.svg",
    "PET_SHOP": "/static/icones/categorias/pet_shop.svg",
    "INFORMATICA": "/static/icones/categorias/informatica.svg",
    "OUTROS": "/static/icones/categorias/outros.svg",
}


def upgrade() -> None:
    conn = op.get_bind()
    for codigo, icone in ICONES_POR_CODIGO.items():
        conn.execute(
            sa.text("UPDATE material_categoria SET icone = :icone WHERE codigo = :codigo"),
            {"icone": icone, "codigo": codigo},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for codigo in ICONES_POR_CODIGO:
        conn.execute(
            sa.text("UPDATE material_categoria SET icone = NULL WHERE codigo = :codigo"),
            {"codigo": codigo},
        )
