# PDV Ibix - Processamento de webhook para pagamentos marketplace
"""Atualiza PaymentTransaction, PedidoMarketplace e reserva de estoque quando o gateway confirma pagamento."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import (
    MarketplaceCheckoutSession,
    MarketplaceCheckoutSessionPedido,
    PaymentTransaction,
    PedidoItemMarketplace,
    PedidoMarketplace,
)
from app.services.payments.status_map import (
    AUTHORIZED,
    CANCELLED,
    CHARGEBACK,
    EXPIRED,
    PAID,
    PARTIALLY_REFUNDED,
    REFUNDED,
    REFUSED,
    can_transition,
)
from app.services.reserva_estoque_marketplace_service import (
    commit_reservation,
    release_reservation,
    restore_marketplace_pedido_stock,
)


def _apply_single_pedido_paid(
    db: Session,
    tx: PaymentTransaction,
    pedido_id: int,
    *,
    gross_for_billing: Optional[Decimal] = None,
) -> None:
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not pedido:
        return
    pedido.status_pagamento = "pago"
    pedido.status_pedido = "confirmado"
    from app.services.pedido_status_evento_service import registrar_pedido_status_evento

    registrar_pedido_status_evento(
        db,
        pedido_id=pedido_id,
        tipo_evento="pagamento_aprovado",
        status_codigo="confirmado",
        status_label="Pedido confirmado",
        actor_type="webhook",
    )
    commit_reservation(db, pedido_id)
    try:
        from app.core.logging import log_error
        from app.services.payments.billing_usage_service import record_payment_billing

        item_count = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == pedido_id).count()
        fmt = getattr(pedido, "formato_frete_snapshot", None) or "sem_frete"
        g_amt = gross_for_billing if gross_for_billing is not None else (tx.amount or Decimal("0"))
        base_amount = pedido.subtotal if fmt == "plataforma" else g_amt
        record_payment_billing(
            db,
            payment_transaction_id=tx.id,
            cliente_id=tx.cliente_id,
            loja_id=pedido.loja_id,
            pedido_id=pedido_id,
            provider=tx.provider_code or "mercadopago",
            provider_payment_id=tx.provider_transaction_id,
            item_count=item_count or 0,
            gross_amount=g_amt,
            percentage_base_amount=base_amount,
        )
    except Exception as e:
        log_error("record_payment_billing falhou (pedido_id=%s)" % pedido_id, exc_info=e)


def _apply_single_pedido_failed(db: Session, pedido_id: int) -> None:
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if pedido:
        pedido.status_pagamento = "pendente"
    release_reservation(db, pedido_id)


def _apply_single_pedido_refunded(db: Session, pedido_id: int) -> None:
    """Pagamento estornado/chargeback após confirmação (webhook ou refund admin)."""
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not pedido:
        return
    if (pedido.status_pagamento or "").strip().lower() == "estornado":
        return
    pedido.status_pagamento = "estornado"
    pedido.status_pedido = "cancelado"
    from app.services.pedido_status_evento_service import registrar_pedido_status_evento

    registrar_pedido_status_evento(
        db,
        pedido_id=pedido_id,
        tipo_evento="pagamento_estornado",
        status_codigo="cancelado",
        status_label="Pagamento estornado",
        actor_type="webhook",
    )
    restore_marketplace_pedido_stock(db, pedido_id)


def _process_session_payment_notification(
    db: Session,
    tx: PaymentTransaction,
    new_status: str,
    provider_payload: Optional[Dict[str, Any]],
) -> bool:
    links = (
        db.query(MarketplaceCheckoutSessionPedido)
        .filter(MarketplaceCheckoutSessionPedido.session_id == tx.checkout_session_id)
        .order_by(MarketplaceCheckoutSessionPedido.sort_order.asc())
        .all()
    )
    pids = [link.pedido_id for link in links]
    sess = db.query(MarketplaceCheckoutSession).filter(MarketplaceCheckoutSession.id == tx.checkout_session_id).first()
    if new_status in (PAID, AUTHORIZED):
        if sess:
            sess.status = "pago"
        for pid in pids:
            pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pid).first()
            gross = Decimal(str(pedido.total)) if pedido and pedido.total is not None else Decimal("0")
            _apply_single_pedido_paid(db, tx, pid, gross_for_billing=gross)
    elif new_status in (REFUNDED, PARTIALLY_REFUNDED, CHARGEBACK):
        if sess and (sess.status or "").strip().lower() != "estornado":
            sess.status = "estornado"
        for pid in pids:
            _apply_single_pedido_refunded(db, pid)
    else:
        if sess:
            sess.status = "cancelado"
        for pid in pids:
            _apply_single_pedido_failed(db, pid)
    return True


def process_payment_notification(
    db: Session,
    tx: PaymentTransaction,
    provider_status: str,
    provider_payload: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Atualiza transação com status do provedor; se paid/authorized, atualiza pedido e baixa estoque
    (comita reserva legada ou grava committed com dedução). Se rejected/cancelled/expired, libera reserva reserved.
    Retorna True se houve alteração relevante.
    """
    from app.services.payments.status_map import to_internal

    new_status = to_internal(tx.provider_code or "mercadopago", provider_status)
    if not can_transition((tx.status or "pending").lower(), new_status):
        return False
    tx.provider_status = provider_status
    tx.status = new_status
    if provider_payload:
        import json

        tx.provider_response = json.dumps(provider_payload) if isinstance(provider_payload, dict) else str(provider_payload)
        pid = provider_payload.get("id")
        if pid is not None:
            tx.provider_transaction_id = str(pid)
    if new_status in (PAID, AUTHORIZED):
        tx.paid_at = datetime.now(timezone.utc)
        tx.reconciliation_status = "matched"
        tx.reconciliation_date = datetime.now(timezone.utc)
        if tx.modo_recebimento == "plataforma" and tx.repasse_status_id is None:
            tx.repasse_status_id = 1
    elif new_status in (REFUSED, CANCELLED, EXPIRED):
        tx.reconciliation_status = "divergence"
        tx.reconciliation_date = datetime.now(timezone.utc)
    elif new_status in (REFUNDED, PARTIALLY_REFUNDED, CHARGEBACK):
        tx.reconciliation_status = "matched"
        tx.reconciliation_date = datetime.now(timezone.utc)
        if not tx.refunded_at:
            tx.refunded_at = datetime.now(timezone.utc)

    if tx.checkout_session_id:
        return _process_session_payment_notification(db, tx, new_status, provider_payload)

    pedido_id = tx.pedido_id
    if not pedido_id:
        return True

    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not pedido:
        return True

    if new_status in (PAID, AUTHORIZED):
        _apply_single_pedido_paid(db, tx, pedido_id, gross_for_billing=None)
    elif new_status in (REFUNDED, PARTIALLY_REFUNDED, CHARGEBACK):
        _apply_single_pedido_refunded(db, pedido_id)
    else:
        _apply_single_pedido_failed(db, pedido_id)
    return True


def apply_marketplace_refund_side_effects(db: Session, tx: PaymentTransaction) -> None:
    """
    Após estorno confirmado no provedor (ex.: admin): propaga para pedidos/sessão como no webhook.
    Idempotente se pedidos já estiverem estornados.
    """
    if not tx:
        return
    if tx.checkout_session_id:
        _process_session_payment_notification(db, tx, REFUNDED, None)
    elif tx.pedido_id:
        _apply_single_pedido_refunded(db, tx.pedido_id)
