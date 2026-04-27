# PDV Ibix - Eventos de cobrança da plataforma (marketplace)
"""Registra evento faturável por pagamento confirmado; reversão em cancelamento/refund (idempotência)."""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models import BillingUsageEvent


def record_payment_billing(
    db: Session,
    payment_transaction_id: int,
    cliente_id: int,
    loja_id: Optional[int],
    pedido_id: Optional[int],
    provider: str,
    provider_payment_id: Optional[str],
    item_count: int,
    gross_amount: Decimal,
    percentage_base_amount: Optional[Decimal] = None,
) -> Optional[BillingUsageEvent]:
    """
    Insere evento faturável (pagamento confirmado). Idempotência: não insere se já existir
    evento para (payment_transaction_id, event_type='payment_confirmed').
    """
    q = (
        db.query(BillingUsageEvent)
        .filter(
            BillingUsageEvent.payment_transaction_id == payment_transaction_id,
            BillingUsageEvent.event_type == "payment_confirmed",
            BillingUsageEvent.is_reversal.is_(False),
        )
    )
    if pedido_id is not None:
        q = q.filter(BillingUsageEvent.pedido_id == pedido_id)
    else:
        q = q.filter(BillingUsageEvent.pedido_id.is_(None))
    existing = q.first()
    if existing:
        return existing
    ev = BillingUsageEvent(
        cliente_id=cliente_id,
        loja_id=loja_id,
        pedido_id=pedido_id,
        payment_transaction_id=payment_transaction_id,
        provider=provider,
        provider_payment_id=provider_payment_id,
        event_type="payment_confirmed",
        item_count_billable=item_count,
        gross_amount_billable=gross_amount,
        percentage_base_amount=percentage_base_amount,
        is_reversal=False,
    )
    db.add(ev)
    return ev


def record_refund_reversal(
    db: Session,
    source_refund_id: int,
    payment_transaction_id: int,
    cliente_id: int,
    amount_reversed: Decimal,
    loja_id: Optional[int] = None,
    pedido_id: Optional[int] = None,
) -> BillingUsageEvent:
    """Registra reversão de cobrança por estorno (idempotência por source_refund_id)."""
    existing = (
        db.query(BillingUsageEvent)
        .filter(
            BillingUsageEvent.source_refund_id == source_refund_id,
            BillingUsageEvent.is_reversal.is_(True),
        )
        .first()
    )
    if existing:
        return existing
    from datetime import datetime, timezone
    ev = BillingUsageEvent(
        cliente_id=cliente_id,
        loja_id=loja_id,
        pedido_id=pedido_id,
        payment_transaction_id=payment_transaction_id,
        event_type="refund_reversal",
        gross_amount_billable=amount_reversed,
        is_reversal=True,
        source_refund_id=source_refund_id,
        reversed_at=datetime.now(timezone.utc),
    )
    db.add(ev)
    return ev
