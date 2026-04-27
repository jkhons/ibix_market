# PDV Ibix - Registro de eventos de status do pedido (timeline para o comprador)
"""Registra eventos na timeline do pedido marketplace para exibição em /loja/acompanhar-pedido."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models import PedidoStatusEvento, StatusPedidoMarketplace

# Labels padrão para status do sistema (não configuráveis)
_LABEL_PADRAO = {
    "aguardando_pagamento": "Aguardando pagamento",
    "confirmado": "Pedido confirmado",
    "cancelado": "Cancelado",
}


def registrar_pedido_status_evento(
    db: Session,
    pedido_id: int,
    tipo_evento: str,
    status_codigo: str,
    status_label: Optional[str] = None,
    actor_type: str = "sistema",
    actor_id: Optional[int] = None,
) -> PedidoStatusEvento:
    """
    Registra um evento na timeline do pedido.
    tipo_evento: pedido_criado | pagamento_aprovado | status_alterado | reatribuicao_comprador
    actor_type: sistema | loja | webhook | super_admin
    """
    if not status_label:
        status_label = _LABEL_PADRAO.get(status_codigo)
        if not status_label:
            st = db.query(StatusPedidoMarketplace).filter(
                StatusPedidoMarketplace.codigo == status_codigo,
                StatusPedidoMarketplace.ativo.is_(True),
            ).first()
            status_label = st.label if st else status_codigo.replace("_", " ").title()

    ev = PedidoStatusEvento(
        pedido_id=pedido_id,
        tipo_evento=tipo_evento,
        status_codigo=status_codigo,
        status_label=status_label,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    db.add(ev)
    db.flush()
    return ev
