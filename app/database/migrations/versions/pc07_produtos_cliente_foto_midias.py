"""Adicionar foto_peca e midias (imagens/vídeos) em produtos_cliente.

Revision ID: pc07_foto_midias
Revises: nfe06_mk_nf
Create Date: 2026-03-08

- foto_peca: caminho da imagem principal (compatível com PDV e vitrine).
- midias: JSON array de { tipo: 'imagem'|'video', url: string } para múltiplas mídias.
"""
import sqlalchemy as sa
from alembic import op

revision = "pc07_foto_midias"
down_revision = "nfe06_mk_nf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "produtos_cliente",
        sa.Column("foto_peca", sa.String(512), nullable=True, comment="Caminho da imagem principal do produto"),
    )
    op.add_column(
        "produtos_cliente",
        sa.Column("midias", sa.Text(), nullable=True, comment="JSON: lista de { tipo, url } para imagens e vídeos"),
    )


def downgrade() -> None:
    op.drop_column("produtos_cliente", "midias")
    op.drop_column("produtos_cliente", "foto_peca")
