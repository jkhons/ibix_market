"""Adiciona colunas NFC-e (CSC) na empresa.

Revision ID: nfce_csc_emp
Revises: nfe_tent_diag
Create Date: 2026-03-13

Configuração NFC-e: nfce_habilitado, nfce_csc_id, nfce_csc_token (modelo 65).
"""
import sqlalchemy as sa
from alembic import op

revision = "nfce_csc_emp"
down_revision = "nfe_tent_diag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "empresa",
        sa.Column("nfce_habilitado", sa.Boolean(), nullable=True, server_default="false", comment="Habilitar emissão NFC-e"),
    )
    op.add_column(
        "empresa",
        sa.Column("nfce_csc_id", sa.String(10), nullable=True, comment="ID do CSC - SEFAZ"),
    )
    op.add_column(
        "empresa",
        sa.Column("nfce_csc_token", sa.String(255), nullable=True, comment="Token CSC (criptografado)"),
    )


def downgrade() -> None:
    op.drop_column("empresa", "nfce_csc_token")
    op.drop_column("empresa", "nfce_csc_id")
    op.drop_column("empresa", "nfce_habilitado")
