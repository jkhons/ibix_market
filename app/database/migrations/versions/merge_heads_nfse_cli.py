"""Merge heads: cli01_cep20 e nfse01b_rps (NFS-e e clientes CEP).

Revision ID: merge_nfse_cli
Revises: cli01_cep20, nfse01b_rps
Create Date: 2026-03-02

"""

revision = "merge_nfse_cli"
down_revision = ("cli01_cep20", "nfse01b_rps")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
