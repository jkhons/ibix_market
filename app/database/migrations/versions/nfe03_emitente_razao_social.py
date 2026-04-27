"""Adicionar emitente_razao_social em nfe_documentos para exibir nome do emissor na listagem.

Revision ID: nfe03_emitente
Revises: cli02_escopo
Create Date: 2026-03-03

Permite exibir o nome do emissor em /negocio/entrada-nfe mesmo quando
emitente_fornecedor_id é NULL (valor vindo do XML na importação).
"""
import sqlalchemy as sa
from alembic import op

revision = "nfe03_emitente"
down_revision = "cli02_escopo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nfe_documentos",
        sa.Column("emitente_razao_social", sa.String(255), nullable=True, comment="Razão social do emitente (XML xNome)"),
    )


def downgrade() -> None:
    op.drop_column("nfe_documentos", "emitente_razao_social")
