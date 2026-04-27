"""fiscal_evento: colunas resposta_bruta, http_content_type, status_http (auditoria SEFAZ).

Revision ID: fiscal_evt_resp
Revises: fiscal_baixar_pdf_ca
Create Date: 2026-03-12

Persistência da resposta bruta e metadados HTTP no evento fiscal (Entrega 4 plano NF-e).
"""
import sqlalchemy as sa
from alembic import op

revision = "fiscal_evt_resp"
down_revision = "fiscal_baixar_pdf_ca"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fiscal_evento", sa.Column("resposta_bruta", sa.Text(), nullable=True, comment="Resposta bruta do webservice (ex.: SEFAZ)"))
    op.add_column("fiscal_evento", sa.Column("http_content_type", sa.String(100), nullable=True, comment="Content-Type do retorno HTTP"))
    op.add_column("fiscal_evento", sa.Column("status_http", sa.Integer(), nullable=True, comment="Código HTTP do retorno (ex.: 200, 400)"))


def downgrade() -> None:
    op.drop_column("fiscal_evento", "status_http")
    op.drop_column("fiscal_evento", "http_content_type")
    op.drop_column("fiscal_evento", "resposta_bruta")
