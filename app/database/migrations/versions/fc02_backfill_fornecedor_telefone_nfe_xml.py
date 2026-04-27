"""Backfill: preencher fornecedores_cliente.telefone a partir de emit/enderEmit/fone no XML armazenado em nfe_documentos.

Revision ID: fc02_forn_tel_nfe_xml
Revises: cx01_caixas_remove_pdvs
Create Date: 2026-04-15

Notas já importadas com xml_original e emitente_fornecedor_id: reaplica o mesmo critério da importação
(só atualiza quando telefone do fornecedor está vazio).
"""
from __future__ import annotations

from alembic import op
from sqlalchemy.orm import Session

revision = "fc02_forn_tel_nfe_xml"
down_revision = "cx01_caixas_remove_pdvs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.services.fiscal.nfe_entrada_service import backfill_fornecedor_telefone_desde_nfe_xml

    bind = op.get_bind()
    session = Session(bind=bind, expire_on_commit=False)
    try:
        backfill_fornecedor_telefone_desde_nfe_xml(session, force=False, yield_per=150)
        session.commit()
    finally:
        session.close()


def downgrade() -> None:
    # Dados derivados de XML; não há como distinguir telefones preenchidos só por este backfill.
    pass
