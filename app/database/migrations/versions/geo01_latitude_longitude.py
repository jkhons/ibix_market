"""Geolocalização: adiciona latitude/longitude em clientes e enderecos_consumidor.

Coordenadas derivadas do CEP via geocodificação (BrasilAPI/Nominatim).
Índices parciais WHERE NOT NULL para não desperdiçar espaço com registros sem coordenada.

Revision ID: geo01_lat_lng
Revises: mob10_indexes_constraints
Create Date: 2026-04-13
"""
import sqlalchemy as sa
from alembic import op

revision = "geo01_lat_lng"
down_revision = "mob10_indexes_constraints"


def upgrade() -> None:
    op.add_column("clientes", sa.Column("latitude", sa.Float, nullable=True))
    op.add_column("clientes", sa.Column("longitude", sa.Float, nullable=True))
    op.add_column("enderecos_consumidor", sa.Column("latitude", sa.Float, nullable=True))
    op.add_column("enderecos_consumidor", sa.Column("longitude", sa.Float, nullable=True))

    op.create_index(
        "idx_clientes_lat_lng",
        "clientes",
        ["latitude", "longitude"],
        postgresql_where=sa.text("latitude IS NOT NULL"),
    )
    op.create_index(
        "idx_enderecos_consumidor_lat_lng",
        "enderecos_consumidor",
        ["latitude", "longitude"],
        postgresql_where=sa.text("latitude IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_enderecos_consumidor_lat_lng", table_name="enderecos_consumidor")
    op.drop_index("idx_clientes_lat_lng", table_name="clientes")
    op.drop_column("enderecos_consumidor", "longitude")
    op.drop_column("enderecos_consumidor", "latitude")
    op.drop_column("clientes", "longitude")
    op.drop_column("clientes", "latitude")
