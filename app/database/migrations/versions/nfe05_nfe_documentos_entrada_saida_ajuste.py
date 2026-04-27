"""Ajustar notas já importadas: entrada_saida SAIDA -> ENTRADA.

Revision ID: nfe05_entrada_aj
Revises: ca_neg_pdv
Create Date: 2026-03-03

No módulo Entrada de Notas o comprador importa XML do fornecedor; do ponto de vista
do estabelecimento é sempre ENTRADA (tpNF no XML é saída do emissor). Corrige documentos
que foram gravados como SAIDA para ENTRADA, permitindo Confirmar e lançar no estoque.
"""
from alembic import op

revision = "nfe05_entrada_aj"
down_revision = "ca_neg_pdv"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE nfe_documentos SET entrada_saida = 'ENTRADA' WHERE entrada_saida = 'SAIDA'"
    )


def downgrade() -> None:
    # Não reverter: manter como ENTRADA; revertendo voltaria SAIDA e bloquearia lançamento
    pass
