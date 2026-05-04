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
from ...services.websocket_manager import publish_event as publish_consumidor_event

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
    # Real-time para o comprador (via pedido -> comprador_id). Best-effort.
    try:
        pid = getattr(entrega, "pedido_id", None)
        if pid:
            from ...models import PedidoMarketplace

            pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pid).first()
            cid = getattr(pedido, "comprador_id", None) if pedido else None
            if cid:
                publish_consumidor_event(
                    int(cid),
                    "entrega.status_alterado",
                    {
                        "entrega_id": entrega.id,
                        "pedido_id": entrega.pedido_id,
                        "status": novo_status,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
    except Exception:
        pass
    try:
        from app.worker.tasks import notificar_marketplace_entrega_status_email_comprador

        notificar_marketplace_entrega_status_email_comprador.delay(entrega.id, novo_status)
    except Exception:
        pass
    return entrega
