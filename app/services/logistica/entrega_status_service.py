# PDV Ibix - Service: atualizar status da entrega (máquina de estados)
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ...core.constants.entrega_status import (
    ACEITA,
    EM_RETIRADA,
    EM_ROTA,
    ENTREGUE,
    FALHA_ENTREGA,
    RETIRADA,
)
from ...models import EntregaEvento, EntregaMarketplace

_TRANSICOES = {
    ACEITA: (EM_RETIRADA,),
    EM_RETIRADA: (RETIRADA,),
    RETIRADA: (EM_ROTA,),
    EM_ROTA: (ENTREGUE, FALHA_ENTREGA),
}


def atualizar_status_entrega(
    db: Session,
    entrega_id: int,
    entregador_id: int,
    novo_status: str,
) -> EntregaMarketplace:
    """
    Atualiza status da entrega. Só o entregador vinculado pode alterar.
    Valida máquina de estados (transição fechada).
    """
    entrega = db.query(EntregaMarketplace).filter(EntregaMarketplace.id == entrega_id).first()
    if not entrega:
        raise ValueError("Entrega não encontrada")
    if entrega.entregador_id != entregador_id:
        raise ValueError("Apenas o entregador vinculado pode alterar o status")

    permitidos = _TRANSICOES.get(entrega.status)
    if not permitidos or novo_status not in permitidos:
        raise ValueError(f"Transição de {entrega.status} para {novo_status} não permitida")

    status_anterior = entrega.status
    agora = datetime.now(timezone.utc)
    entrega.status = novo_status
    if novo_status == EM_RETIRADA:
        pass
    elif novo_status == RETIRADA:
        entrega.retirada_em = agora
    elif novo_status == EM_ROTA:
        entrega.saiu_para_entrega_em = agora
    elif novo_status == ENTREGUE:
        entrega.entregue_em = agora
    elif novo_status == FALHA_ENTREGA:
        pass

    ev = EntregaEvento(
        entrega_id=entrega.id,
        tipo_evento=f"status_{novo_status}",
        actor_type="entregador",
        actor_id=entregador_id,
        payload_json={"status_anterior": status_anterior, "novo_status": novo_status},
    )
    db.add(ev)
    db.commit()
    db.refresh(entrega)
    return entrega
