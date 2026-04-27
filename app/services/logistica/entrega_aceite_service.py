# PDV Ibix - Service: aceitar entrega (com lock transacional)
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.constants.entrega_status import ACEITA, DISPONIVEL
from ...models import EntregaMarketplace


def aceitar_entrega(db: Session, entrega_id: int, entregador_id: int) -> EntregaMarketplace:
    """
    Associa entregador à entrega com lock (SELECT FOR UPDATE).
    Retorna a entrega atualizada ou levanta ValueError se já aceita ou estado inválido.
    """
    stmt = select(EntregaMarketplace).where(EntregaMarketplace.id == entrega_id).with_for_update()
    entrega = db.execute(stmt).scalars().one_or_none()
    if not entrega:
        raise ValueError("Entrega não encontrada")
    if entrega.status != DISPONIVEL:
        raise ValueError("Entrega não está disponível para aceite")
    if entrega.entregador_id is not None:
        raise ValueError("Entrega já foi aceita por outro entregador")

    agora = datetime.now(timezone.utc)
    entrega.entregador_id = entregador_id
    entrega.status = ACEITA
    entrega.aceita_em = agora

    from ...models import EntregaEvento
    ev = EntregaEvento(
        entrega_id=entrega.id,
        tipo_evento="entrega_aceita",
        actor_type="entregador",
        actor_id=entregador_id,
        payload_json={"entregador_id": entregador_id},
    )
    db.add(ev)
    db.commit()
    db.refresh(entrega)
    return entrega
