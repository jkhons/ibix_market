"""Adiciona colunas de diagnóstico em nfe_tentativa_envio (cstat, xmotivo, nrec, tipo_resultado, etc).

Revision ID: nfe_tent_diag
Revises: seed_regras_qualquer
Create Date: 2026-03-13

Plano NF-e emissão SEFAZ: tornar nfe_tentativa_envio fonte principal de diagnóstico.
"""
import sqlalchemy as sa
from alembic import op

revision = "nfe_tent_diag"
down_revision = "seed_regras_qualquer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nfe_tentativa_envio",
        sa.Column("cstat", sa.String(10), nullable=True, comment="cStat SEFAZ (protNFe.infProt ou retEnviNFe)"),
    )
    op.add_column(
        "nfe_tentativa_envio",
        sa.Column("xmotivo", sa.Text(), nullable=True, comment="xMotivo SEFAZ"),
    )
    op.add_column(
        "nfe_tentativa_envio",
        sa.Column("nrec", sa.String(20), nullable=True, comment="nRec (recibo) quando lote 103"),
    )
    op.add_column(
        "nfe_tentativa_envio",
        sa.Column("protocolo", sa.String(50), nullable=True, comment="Protocolo nProt"),
    )
    op.add_column(
        "nfe_tentativa_envio",
        sa.Column("url", sa.String(255), nullable=True, comment="URL do webservice SEFAZ"),
    )
    op.add_column(
        "nfe_tentativa_envio",
        sa.Column("erro_tecnico", sa.Text(), nullable=True, comment="Exceção técnica (timeout, SSL, etc.)"),
    )
    op.add_column(
        "nfe_tentativa_envio",
        sa.Column(
            "tipo_resultado",
            sa.String(30),
            nullable=True,
            comment="erro_tecnico, lote_recebido, lote_processado, autorizada, rejeitada, resposta_invalida",
        ),
    )
    op.add_column(
        "nfe_tentativa_envio",
        sa.Column("resposta_bruta_path", sa.String(500), nullable=True, comment="Path do XML de retorno quando excede limite da coluna"),
    )


def downgrade() -> None:
    op.drop_column("nfe_tentativa_envio", "resposta_bruta_path")
    op.drop_column("nfe_tentativa_envio", "tipo_resultado")
    op.drop_column("nfe_tentativa_envio", "erro_tecnico")
    op.drop_column("nfe_tentativa_envio", "url")
    op.drop_column("nfe_tentativa_envio", "protocolo")
    op.drop_column("nfe_tentativa_envio", "nrec")
    op.drop_column("nfe_tentativa_envio", "xmotivo")
    op.drop_column("nfe_tentativa_envio", "cstat")
