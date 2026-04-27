# PDV Ibix - Serviço de estorno (marketplace)
"""Solicita estorno no provedor e persiste Refund; opcionalmente registra billing reversal."""
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import PaymentTransaction, Refund
from app.services.payments.credentials import decrypt_credentials
from app.services.payments.factory import get_provider_for_cliente


def request_refund(
    db: Session,
    payment_transaction_id: int,
    amount: Optional[Decimal] = None,
    reason: Optional[str] = None,
    requested_by_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Cria registro Refund, chama provedor.refund e atualiza status.
    amount=None = estorno total.
    """
    tx = db.query(PaymentTransaction).filter(PaymentTransaction.id == payment_transaction_id).first()
    if not tx:
        raise ValueError("Transação não encontrada")
    if (tx.status or "").lower() not in ("paid", "authorized"):
        raise ValueError("Apenas transações pagas ou autorizadas podem ser estornadas")
    provider_payment_id = tx.provider_transaction_id
    if not provider_payment_id:
        raise ValueError("Transação sem ID no provedor")

    is_marketplace = bool(tx.pedido_id or getattr(tx, "checkout_session_id", None))
    if is_marketplace:
        from app.services.payments.checkout_marketplace_service import _resolve_provider_and_credentials

        try:
            provider_code_resolved, provider, credentials, _ = _resolve_provider_and_credentials(db, tx.cliente_id)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        result = provider.refund(str(provider_payment_id), amount=amount, credentials=credentials)
        config_provider_code = provider_code_resolved
    else:
        config, provider = get_provider_for_cliente(db, tx.cliente_id)
        if not config or not provider:
            raise ValueError("Provedor não configurado")
        credentials = decrypt_credentials(config.credentials_encrypted)
        result = provider.refund(provider_payment_id, amount=amount, credentials=credentials)
        config_provider_code = config.provider_code
    refund_type = "partial" if amount is not None and amount > 0 and amount < (tx.amount or 0) else "full"
    status_refund = "completed" if result.get("success") else "failed"
    ref = Refund(
        payment_transaction_id=tx.id,
        provider_code=tx.provider_code or config_provider_code,
        provider_refund_id=result.get("provider_refund_id"),
        refund_type=refund_type,
        amount=amount if amount is not None else (tx.amount or 0),
        status=status_refund,
        reason=reason,
        requested_by_user_id=requested_by_user_id,
        payload_json=str(result) if result else None,
    )
    if result.get("success"):
        from datetime import datetime, timezone
        ref.confirmed_at = datetime.now(timezone.utc)
        tx.status = "refunded"
        tx.refunded_at = ref.confirmed_at
    db.add(ref)
    db.flush()
    if result.get("success"):
        try:
            from app.core.logging import log_error
            from app.models import PedidoMarketplace
            from app.services.payments.billing_usage_service import record_refund_reversal
            from app.services.payments.webhook_marketplace_service import apply_marketplace_refund_side_effects

            apply_marketplace_refund_side_effects(db, tx)

            if getattr(tx, "checkout_session_id", None):
                record_refund_reversal(
                    db,
                    source_refund_id=ref.id,
                    payment_transaction_id=tx.id,
                    cliente_id=tx.cliente_id,
                    amount_reversed=ref.amount,
                    loja_id=None,
                    pedido_id=None,
                )
            else:
                pedido = (
                    db.query(PedidoMarketplace).filter(PedidoMarketplace.id == tx.pedido_id).first()
                    if tx.pedido_id
                    else None
                )
                record_refund_reversal(
                    db,
                    source_refund_id=ref.id,
                    payment_transaction_id=tx.id,
                    cliente_id=tx.cliente_id,
                    amount_reversed=ref.amount,
                    loja_id=pedido.loja_id if pedido else None,
                    pedido_id=tx.pedido_id,
                )
        except Exception as e:
            log_error("record_refund_reversal falhou (refund_id=%s)" % ref.id, exc_info=e)
    db.commit()
    db.refresh(ref)
    return {
        "refund_id": ref.id,
        "success": result.get("success", False),
        "provider_refund_id": result.get("provider_refund_id"),
        "message": result.get("message"),
    }
