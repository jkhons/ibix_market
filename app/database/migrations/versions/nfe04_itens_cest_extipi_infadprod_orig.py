"""Adicionar colunas fiscais em nfe_itens: cest_xml, extipi_xml, infadprod_xml, orig_xml.

Revision ID: nfe04_itens
Revises: nfe03_emitente
Create Date: 2026-03-03

Layout NFe 4.0: importação completa para rastreio e produto padronizado para saída com NF.
"""
import sqlalchemy as sa
from alembic import op

revision = "nfe04_itens"
down_revision = "nfe03_emitente"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nfe_itens",
        sa.Column("cest_xml", sa.String(10), nullable=True, comment="CEST do item (XML)"),
    )
    op.add_column(
        "nfe_itens",
        sa.Column("extipi_xml", sa.String(5), nullable=True, comment="EX TIPI do item (XML)"),
    )
    op.add_column(
        "nfe_itens",
        sa.Column("infadprod_xml", sa.Text(), nullable=True, comment="Informações adicionais do produto (XML infAdProd)"),
    )
    op.add_column(
        "nfe_itens",
        sa.Column("orig_xml", sa.Integer(), nullable=True, comment="Origem da mercadoria 0-8 (XML det/imposto/ICMS/orig)"),
    )


def downgrade() -> None:
    op.drop_column("nfe_itens", "orig_xml")
    op.drop_column("nfe_itens", "infadprod_xml")
    op.drop_column("nfe_itens", "extipi_xml")
    op.drop_column("nfe_itens", "cest_xml")
