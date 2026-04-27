"""Seed configuração ISO 17025: certificados apenas via procedimento

Revision ID: a78cd580j5k2
Revises: b67cc569p4y1
Create Date: 2026-02-08

Adiciona configuração iso_17025_certificados_apenas_processo = true.
Quando ativa, bloqueia criação direta de certificados (POST /certificados) e
exige que certificados sejam emitidos via procedimento completo.
"""
from alembic import op
from sqlalchemy import text

revision = "a78cd580j5k2"
down_revision = "b67cc569p4y1"
branch_labels = None
depends_on = None

CHAVE = "iso_17025_certificados_apenas_processo"
VALOR = "true"
DESCRICAO = "ISO 17025: certificados apenas via procedimento completo. Quando true, bloqueia POST /certificados e exige emissão via POST /processos/{id}/certificados."


def upgrade() -> None:
    conn = op.get_bind()
    r = conn.execute(
        text("SELECT 1 FROM configuracoes WHERE chave = :chave"),
        {"chave": CHAVE},
    ).fetchone()
    if not r:
        conn.execute(
            text("""
                INSERT INTO configuracoes (chave, valor, descricao, created_at, updated_at)
                VALUES (:chave, :valor, :descricao, NOW(), NOW())
            """),
            {"chave": CHAVE, "valor": VALOR, "descricao": DESCRICAO},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("DELETE FROM configuracoes WHERE chave = :chave"),
        {"chave": CHAVE},
    )
