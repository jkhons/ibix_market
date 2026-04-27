# PDV Ibix - Serviço de Orçamento (Módulo Orçamento e Pedido)
"""Lógica de negócio para orçamentos: expiração, validação."""
from datetime import date

from sqlalchemy.orm import Session

from app.models import Orcamento


def expirar_orcamentos(db: Session, cliente_id: int | None = None) -> int:
    """
    Marca como 'expirado' orçamentos com data_validade < hoje e status em (emitido, aprovado, rascunho).
    Se cliente_id for informado, restringe ao estabelecimento.
    Retorna quantidade de orçamentos atualizados.
    """
    q = db.query(Orcamento).filter(
        Orcamento.data_validade < date.today(),
        Orcamento.status.in_(("rascunho", "emitido", "aprovado")),
    )
    if cliente_id is not None:
        q = q.filter(Orcamento.cliente_id == cliente_id)
    rows = q.all()
    for o in rows:
        o.status = "expirado"
    if rows:
        db.commit()
    return len(rows)


def validar_para_conversao(db: Session, orcamento_id: int) -> tuple[bool, str]:
    """
    Verifica se o orçamento pode ser convertido em pedido.
    Retorna (True, "") se OK, (False, "motivo") se não.
    """
    o = db.query(Orcamento).filter(Orcamento.id == orcamento_id).first()
    if not o:
        return False, "Orçamento não encontrado"
    if o.status not in ("emitido", "aprovado"):
        return False, f"Orçamento deve estar emitido ou aprovado (status atual: {o.status})"
    if o.data_validade < date.today():
        return False, "Orçamento expirado"
    if o.convertido_em_pedido_id:
        return False, "Orçamento já convertido em pedido"
    return True, ""
