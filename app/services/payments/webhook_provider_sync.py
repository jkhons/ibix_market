# PDV Ibix — Processamento síncrono de webhook PagBank / Pagar.me / MP (rota payments)
"""Atualiza PaymentTransaction; marketplace (pedido ou sessão mcs:) delega a process_payment_notification."""
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.services.payments.status_map import is_terminal, to_internal
from app.services.payments.webhook_transaction_lookup import resolve_marketplace_payment_transaction


def apply_provider_webhook(db: Session, code: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    code: pagbank | pagarme | mercadopago
    Retorno: received, processed, reason?, order_id?, new_status?
    """
    from app.services.payments.status_map import can_transition

    code = (code or "").strip().lower()
    order_id = None
    raw_status = None
    external_reference = None

    if code == "pagbank":
        charges = payload.get("charges") or []
        order_id = payload.get("id")
        external_reference = payload.get("reference_id")
        if charges:
            raw_status = (charges[0].get("status") or "WAITING").lower()
        else:
            raw_status = "pending"

    elif code == "pagarme":
        event_data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        order_id = event_data.get("id")
        external_reference = event_data.get("code") or payload.get("code")
        raw_status = (event_data.get("status") or "pending").lower()

    elif code == "mercadopago":
        data_obj = payload.get("data") or {}
        mp_payment_id = data_obj.get("id")
        if mp_payment_id is not None:
            order_id = str(mp_payment_id)
        action = payload.get("action")
        if action:
            raw_status = str(action).lower()
        external_reference = data_obj.get("external_reference")

    else:
        return {"received": False, "processed": False, "reason": "provedor não suportado"}

    if not order_id and not (external_reference and str(external_reference).strip()):
        return {
            "received": True,
            "processed": False,
            "reason": "order_id ou reference_id/code ausente no payload",
        }

    raw_status = (raw_status or "pending").lower()

    tx = resolve_marketplace_payment_transaction(
        db,
        code,
        order_id=str(order_id).strip() if order_id is not None and str(order_id).strip() else None,
        external_reference=str(external_reference).strip() if external_reference else None,
    )

    if not tx:
        return {
            "received": True,
            "processed": False,
            "reason": "Transação não encontrada para o identificador informado.",
        }

    if tx.pedido_id or getattr(tx, "checkout_session_id", None):
        from app.services.payments.webhook_marketplace_service import (
            dispatch_marketplace_pedido_pagamento_confirmado_notifications,
            process_payment_notification,
        )

        mp_res = process_payment_notification(db, tx, raw_status, payload)
        if mp_res:
            db.commit()
            dispatch_marketplace_pedido_pagamento_confirmado_notifications(
                mp_res.pedido_ids_notify_pagamento_confirmado
            )
            return {
                "received": True,
                "processed": True,
                "order_id": order_id,
                "new_status": tx.status,
                "transaction_uuid": tx.uuid,
            }
        db.rollback()
        return {
            "received": True,
            "processed": False,
            "reason": "Transição de status não aplicada (já finalizado ou inválido).",
        }

    internal_status = to_internal(code, raw_status)

    if can_transition((tx.status or "pending").lower(), internal_status):
        tx.status = internal_status
        if internal_status == "paid":
            from datetime import datetime as _dt

            tx.paid_at = _dt.utcnow()
        elif internal_status == "refunded":
            from datetime import datetime as _dt

            tx.refunded_at = _dt.utcnow()
        tx.reconciliation_status = "reconciled" if is_terminal(internal_status) else "pending"
        db.commit()
        return {
            "received": True,
            "processed": True,
            "order_id": order_id,
            "new_status": internal_status,
        }
    return {
        "received": True,
        "processed": False,
        "reason": f"Transição {tx.status} -> {internal_status} não permitida",
    }
