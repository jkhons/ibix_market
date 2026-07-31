"""Geração de número sequencial de venda (V-YY-SEQ). Reutilizado por API de vendas e por Enviar para vendas (OS)."""
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.document_ref import build_doc_ref, doc_ref_like_patterns, next_seq_for_year
from app.models.venda import Venda


def gerar_numero_venda(db: Session) -> str:
    """Gera próximo número de venda no formato compacto V-YY-SEQ."""
    ano_atual = datetime.now().year
    patterns = doc_ref_like_patterns("V", ano_atual)
    vendas = (
        db.query(Venda.numero_venda)
        .filter(or_(*[Venda.numero_venda.like(p) for p in patterns]))
        .all()
    )
    proximo_numero = next_seq_for_year(
        (row[0] for row in vendas),
        ano_atual,
        prefix="V",
    )
    return build_doc_ref("V", proximo_numero, ano_atual)
