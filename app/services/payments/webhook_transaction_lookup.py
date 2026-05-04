# PDV Ibix — Resolver PaymentTransaction em webhooks (PagBank, Pagar.me, etc.)
"""Suporta pedido marketplace por ID numérico e checkout unificado external_reference mcs:{uuid}."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models import MarketplaceCheckoutSession, PaymentTransaction


def find_transaction_for_provider_order(
    db: Session, provider_code: str, order_id: Optional[str]
) -> Optional[PaymentTransaction]:
    if not order_id:
        return None
    prov = (provider_code or "").strip().lower()
    oid = str(order_id).strip()
    if not prov or not oid:
        return None
    return (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.provider_code == prov,
            PaymentTransaction.provider_transaction_id == oid,
        )
        .order_by(PaymentTransaction.id.desc())
        .first()
    )


def find_transaction_by_external_reference_for_provider(
    db: Session, provider_code: str, external_reference: str
) -> Optional[PaymentTransaction]:
    """
    Marketplace: external_reference = pedido_id (preferência) ou mcs:{session_uuid}.
    Filtra por provider_code (pagbank, pagarme, mercadopago).
    """
    if not (external_reference or "").strip():
        return None
    er = (external_reference or "").strip()
    prov = (provider_code or "").strip().lower()
    if er.startswith("mcs:"):
        suid = er[4:].strip()
        if suid:
            sess = db.query(MarketplaceCheckoutSession).filter(MarketplaceCheckoutSession.uuid == suid).first()
            if sess:
                tx_active = (
                    db.query(PaymentTransaction)
                    .filter(
                        PaymentTransaction.provider_code == prov,
                        PaymentTransaction.checkout_session_id == sess.id,
                        PaymentTransaction.is_active.is_(True),
                    )
                    .order_by(PaymentTransaction.id.desc())
                    .first()
                )
                if tx_active:
                    return tx_active
                return (
                    db.query(PaymentTransaction)
                    .filter(
                        PaymentTransaction.provider_code == prov,
                        PaymentTransaction.checkout_session_id == sess.id,
                    )
                    .order_by(PaymentTransaction.id.desc())
                    .first()
                )
    try:
        pedido_id = int(er)
        tx_active = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.provider_code == prov,
                PaymentTransaction.pedido_id == pedido_id,
                PaymentTransaction.is_active.is_(True),
            )
            .order_by(PaymentTransaction.id.desc())
            .first()
        )
        if tx_active:
            return tx_active
        return (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.provider_code == prov,
                PaymentTransaction.pedido_id == pedido_id,
            )
            .order_by(PaymentTransaction.id.desc())
            .first()
        )
    except (ValueError, TypeError):
        pass
    return None


def resolve_marketplace_payment_transaction(
    db: Session,
    provider_code: str,
    *,
    order_id: Optional[str] = None,
    external_reference: Optional[str] = None,
) -> Optional[PaymentTransaction]:
    """Resolve transação: prioriza provider_transaction_id == order_id; senão reference_id/code."""
    tx = find_transaction_for_provider_order(db, provider_code, order_id)
    if tx:
        return tx
    if external_reference and (external_reference or "").strip():
        return find_transaction_by_external_reference_for_provider(db, provider_code, external_reference.strip())
    return None
