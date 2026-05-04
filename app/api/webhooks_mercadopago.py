# PDV Ibix - Webhook Mercado Pago (POST /api/webhooks/mercadopago)
# Para receber apenas Webhooks assinados (não IPN), cadastre a URL com ?source_news=webhooks
# Ex.: https://www.ibix.com.br/api/webhooks/mercadopago?source_news=webhooks
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.logging import log_error, log_struct
from app.core.mp_webhook_secrets import list_mp_webhook_secret_candidates
from app.core.rate_limiter import check_webhook_rate_limit
from app.core.webhook_metrics import (
    webhook_processed_total,
    webhook_processing_error_total,
    webhook_queued_total,
    webhook_received_total,
    webhook_signature_invalid_total,
)
from app.database.connection import get_db
from app.integrations.mercadopago import MercadoPagoClient, verify_webhook_signature
from app.models import PaymentProviderConfig, PaymentTransaction, VendaPagamento, WebhookEvent
from app.services import billing_service
from app.services.payments.credentials import decrypt_credentials
from app.services.payments.providers_marketplace import get_marketplace_provider

router = APIRouter()

# Diagnóstico do webhook MP: definir MP_WEBHOOK_DEBUG=true para logar request e resultado da verificação
MP_WEBHOOK_DEBUG = os.getenv("MP_WEBHOOK_DEBUG", "").lower() == "true"


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        # Mercado Pago costuma retornar ISO com Z
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _mp_status_to_internal(mp_status: str) -> str:
    status_raw = (mp_status or "").lower()
    mapping = {
        "approved": "paid",
        "authorized": "authorized",
        "in_process": "pending",
        "pending": "pending",
        "rejected": "failed",
        "cancelled": "cancelled",
        "refunded": "refunded",
        "charged_back": "failed",
    }
    return mapping.get(status_raw, "pending")


def _method_to_forma(method: Optional[str]) -> Optional[str]:
    mapping = {
        "credit": "cartao_credito",
        "debit": "cartao_debito",
        "pix": "pix",
        "boleto": "boleto",
    }
    return mapping.get((method or "").lower())


async def _fetch_mp_payment_with_any_token(db: Session, payment_id: int) -> Optional[Dict[str, Any]]:
    from app.core.billing_config import get_mp_access_token
    token = get_mp_access_token(db)
    if token:
        try:
            client = MercadoPagoClient(token)
            return await client.fetch_payment(payment_id)
        except Exception as exc:
            log_error(
                "mp_fetch_payment billing_token failed payment_id=%s: %s" % (payment_id, exc),
                exc_info=exc,
            )

    configs = (
        db.query(PaymentProviderConfig)
        .filter(PaymentProviderConfig.provider_code == "mercadopago", PaymentProviderConfig.is_active == True)
        .order_by(PaymentProviderConfig.id.desc())
        .limit(50)
        .all()
    )
    for cfg in configs:
        creds = decrypt_credentials(cfg.credentials_encrypted) or {}
        cfg_token = creds.get("access_token") or creds.get("ACCESS_TOKEN") or creds.get("token")
        if not cfg_token:
            continue
        try:
            client = MercadoPagoClient(cfg_token)
            return await client.fetch_payment(payment_id)
        except Exception as exc:
            log_error(
                "mp_fetch_payment config_id=%s cliente_id=%s failed payment_id=%s: %s"
                % (cfg.id, cfg.cliente_id, payment_id, exc),
                exc_info=exc,
            )
            continue
    return None


def _fetch_mp_payment_sync(db: Session, payment_id: int) -> Optional[Dict[str, Any]]:
    """Busca pagamento MP de forma síncrona (para task Celery G2)."""
    from app.core.billing_config import get_mp_access_token

    provider = get_marketplace_provider("mercadopago")

    billing_token = get_mp_access_token(db)
    if billing_token:
        try:
            result = provider.fetch_payment(str(payment_id), {"access_token": billing_token})
            if result:
                return result
        except Exception as exc:
            log_error(
                "mp_fetch_payment_sync billing_token failed payment_id=%s: %s" % (payment_id, exc),
                exc_info=exc,
            )

    configs = (
        db.query(PaymentProviderConfig)
        .filter(PaymentProviderConfig.provider_code == "mercadopago", PaymentProviderConfig.is_active == True)
        .order_by(PaymentProviderConfig.id.desc())
        .limit(50)
        .all()
    )
    for cfg in configs:
        creds = decrypt_credentials(cfg.credentials_encrypted) or {}
        if not (creds.get("access_token") or creds.get("ACCESS_TOKEN") or creds.get("token")):
            continue
        try:
            result = provider.fetch_payment(str(payment_id), creds)
            if result:
                return result
        except Exception as exc:
            log_error(
                "mp_fetch_payment_sync config_id=%s cliente_id=%s failed payment_id=%s: %s"
                % (cfg.id, cfg.cliente_id, payment_id, exc),
                exc_info=exc,
            )
            continue
    return None


def _find_transaction_by_external_reference(db: Session, external_reference: str) -> Optional[PaymentTransaction]:
    """Encontra PaymentTransaction por external_reference (MP). Marketplace usa pedido_id; checkout unificado mcs:{uuid}; PDV pode usar idempotency_key no JSON."""
    if not (external_reference or "").strip():
        return None
    er = (external_reference or "").strip()
    from app.services.payments.webhook_transaction_lookup import find_transaction_by_external_reference_for_provider

    tx_m = find_transaction_by_external_reference_for_provider(db, "mercadopago", er)
    if tx_m:
        return tx_m
    # Fallback: busca por idempotency_key ou external_reference no JSON (PDV/legado)
    for key in ("idempotency_key", "external_reference"):
        like_needle = f'"{key}": "{er}"'
        tx = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.provider_code == "mercadopago")
            .filter(PaymentTransaction.provider_response.ilike(f"%{like_needle}%"))
            .order_by(PaymentTransaction.id.desc())
            .first()
        )
        if tx:
            return tx
    return None


def _find_transaction_for_mp_payment(
    db: Session, external_reference: str, payment_id: Optional[int]
) -> Optional[PaymentTransaction]:
    """
    Resolve transação MP: external_reference (pedido numérico ou mcs:{uuid});
    fallback por provider_transaction_id = payment_id (notificação sem reference confiável).
    """
    tx = _find_transaction_by_external_reference(db, external_reference)
    if tx:
        return tx
    if payment_id is None:
        return None
    pid = str(payment_id).strip()
    if not pid:
        return None
    return (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.provider_code == "mercadopago",
            PaymentTransaction.provider_transaction_id == pid,
        )
        .order_by(PaymentTransaction.id.desc())
        .first()
    )


def _sync_venda_pagamento_from_transaction(db: Session, tx: PaymentTransaction) -> None:
    if not tx.venda_id:
        return
    forma = _method_to_forma(tx.payment_method)
    if not forma:
        return
    query = db.query(VendaPagamento).filter(VendaPagamento.venda_id == tx.venda_id, VendaPagamento.forma == forma)
    if tx.provider_transaction_id:
        row = query.filter(VendaPagamento.id_externo == tx.provider_transaction_id).first()
        if row:
            row.status = "confirmado" if tx.status in {"paid", "authorized"} else "pendente"
            row.observacao = f"Status gateway: {tx.status}"
            return
    row = query.filter(VendaPagamento.status.in_(["pendente", "confirmado"])).order_by(VendaPagamento.id.desc()).first()
    if row:
        row.id_externo = tx.provider_transaction_id or row.id_externo
        row.status = "confirmado" if tx.status in {"paid", "authorized"} else "pendente"
        row.observacao = f"Status gateway: {tx.status}"
        return
    # PDV/gateway: nenhum VendaPagamento existia; criar um para manter venda_pagamentos consistente com a transação.
    # Reconsulta antes de criar (evita duplicata em retentativas do webhook em produção).
    row = query.order_by(VendaPagamento.id.desc()).first()
    if row:
        row.id_externo = tx.provider_transaction_id or row.id_externo
        row.status = "confirmado" if tx.status in {"paid", "authorized"} else "pendente"
        row.observacao = f"Status gateway: {tx.status}"
        return
    valor = tx.amount if tx.amount is not None else Decimal("0")
    novo = VendaPagamento(
        venda_id=tx.venda_id,
        forma=forma,
        valor=valor,
        status="confirmado" if tx.status in {"paid", "authorized"} else "pendente",
        id_externo=tx.provider_transaction_id,
        observacao=f"Status gateway: {tx.status}",
    )
    db.add(novo)


def process_webhook_event_by_id_sync(db: Session, webhook_event_id: int) -> bool:
    """
    Processa um WebhookEvent já persistido (G2: task assíncrona ou reprocessamento).
    Retorna True se processou com sucesso, False caso contrário (já processado, fetch falhou, tx não encontrada).
    """
    ev = db.query(WebhookEvent).filter(WebhookEvent.id == webhook_event_id).first()
    if not ev or ev.processed_at:
        return False
    if ev.provider != "mercadopago":
        return False
    try:
        payment_id = int(ev.provider_payment_id or 0)
    except (ValueError, TypeError):
        ev.last_processing_error = "invalid_provider_payment_id"
        ev.processing_attempts = (ev.processing_attempts or 0) + 1
        db.commit()
        return False
    mp_payment = _fetch_mp_payment_sync(db, payment_id)
    if not mp_payment:
        ev.last_processing_error = "fetch_failed"
        ev.processing_attempts = (ev.processing_attempts or 0) + 1
        db.commit()
        return False
    external_reference = str(mp_payment.get("external_reference") or "")
    tx = _find_transaction_for_mp_payment(db, external_reference, payment_id)
    if not tx:
        ev.last_processing_error = "tx_not_found"
        ev.processing_attempts = (ev.processing_attempts or 0) + 1
        db.commit()
        return False
    mp_status = (mp_payment.get("status") or "").lower()
    pedido_ids_notify_mp: list[int] = []
    if tx.pedido_id or getattr(tx, "checkout_session_id", None):
        from app.services.payments.webhook_marketplace_service import process_payment_notification

        mp_pay_result = process_payment_notification(db, tx, mp_status, mp_payment)
        pedido_ids_notify_mp = mp_pay_result.pedido_ids_notify_pagamento_confirmado
    else:
        tx.status = _mp_status_to_internal(mp_status)
        tx.provider_response = json.dumps(
            {"idempotency_key": external_reference, "payment_details": mp_payment}
        )
        tx.provider_transaction_id = str(mp_payment.get("id") or tx.provider_transaction_id or "")
        approved_at = _parse_datetime(mp_payment.get("date_approved"))
        if approved_at:
            tx.paid_at = approved_at
        if tx.status in {"paid", "authorized"}:
            tx.reconciliation_status = "matched"
            tx.reconciliation_date = datetime.now(timezone.utc)
        elif tx.status in {"failed", "cancelled"}:
            tx.reconciliation_status = "divergence"
            tx.reconciliation_date = datetime.now(timezone.utc)
        _sync_venda_pagamento_from_transaction(db, tx)
    ev.processed_at = datetime.now(timezone.utc)
    ev.processing_attempts = (ev.processing_attempts or 0) + 1
    ev.payment_transaction_id = tx.id
    ev.normalized_status = tx.status
    db.commit()
    if pedido_ids_notify_mp:
        from app.services.payments.webhook_marketplace_service import (
            dispatch_marketplace_pedido_pagamento_confirmado_notifications,
        )

        dispatch_marketplace_pedido_pagamento_confirmado_notifications(pedido_ids_notify_mp)
    return True


@router.post("/mercadopago")
async def mercadopago_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_signature: Optional[str] = Header(None, alias="x-signature"),
    x_request_id: Optional[str] = Header(None, alias="x-request-id"),
    _: None = Depends(check_webhook_rate_limit),
):
    """
    Recebe notificações de pagamento do Mercado Pago (POST).
    Segurança: só processa requisições com assinatura x-signature válida (HMAC-SHA256 com Webhook Secret).
    Sem exceções: qualquer payload sem assinatura válida retorna 401.
    """
    body = await request.body()
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON inválido")

    # Log dos valores do webhook enviado pelo Mercado Pago (para diagnóstico/teste)
    log_struct(
        "mp_webhook_received",
        level="info",
        request_id=getattr(request.state, "request_id", None),
        query_params=dict(request.query_params) if request.query_params else {},
        x_signature=x_signature,
        x_request_id=x_request_id,
        webhook_payload=data,
    )

    # Doc. MP: data.id deve vir da query literal (request.query_params.get("data.id"))
    data_id_query = request.query_params.get("data.id") if request.query_params else None
    data_id_body = (data.get("data") or {}).get("id") if isinstance(data.get("data"), dict) else None

    event_type = data.get("type") or ""
    data_obj = data.get("data") or {}
    payment_id_raw = data_obj.get("id")
    payment_id: Optional[int] = None
    try:
        payment_id = int(payment_id_raw) if payment_id_raw is not None else None
    except (ValueError, TypeError):
        pass

    raw_body_str = body.decode("utf-8", errors="replace")[:50000]
    headers_safe = {k: v for k, v in (request.headers.items() if hasattr(request, "headers") else []) if k.lower() not in ("authorization", "cookie")}

    webhook_ev: Optional[WebhookEvent] = None
    if event_type == "payment" and payment_id is not None:
        event_key = f"mercadopago:payment:{payment_id}"
        webhook_ev = (
            db.query(WebhookEvent)
            .filter(WebhookEvent.provider == "mercadopago", WebhookEvent.event_key == event_key)
            .first()
        )
        if webhook_ev and webhook_ev.processed_at:
            return {"status": "ok", "idempotent": True}
        if not webhook_ev:
            webhook_ev = WebhookEvent(
                provider="mercadopago",
                event_key=event_key,
                event_type=event_type,
                provider_payment_id=str(payment_id),
                signature_valid=False,
                headers_json=json.dumps(headers_safe) if headers_safe else None,
                query_params_json=json.dumps(dict(request.query_params)) if request.query_params else None,
                raw_json=raw_body_str,
                received_at=datetime.now(timezone.utc),
            )
            db.add(webhook_ev)
            db.flush()

    secrets = list_mp_webhook_secret_candidates(db)

    if MP_WEBHOOK_DEBUG:
        log_struct(
            "mp_webhook_request",
            level="info",
            request_id=getattr(request.state, "request_id", None),
            query_params=dict(request.query_params) if request.query_params else {},
            data_id_query=data_id_query,
            data_id_body=data_id_body,
            has_x_signature=bool(x_signature and x_signature.strip()),
            has_x_request_id=bool(x_request_id and str(x_request_id).strip()),
            candidate_secrets_count=len(secrets),
        )
        for i, s in enumerate(secrets):
            masked = (s[:4] + "..." + s[-4:]) if s and len(s) >= 8 else "short-or-empty"
            log_struct(
                "mp_webhook_secret_loaded",
                level="info",
                request_id=getattr(request.state, "request_id", None),
                candidate_index=i,
                masked_secret=masked,
            )

    if not secrets:
        log_struct(
            "mp_webhook_fail",
            level="warning",
            request_id=getattr(request.state, "request_id", None),
            reason="missing_secret",
            query_params=dict(request.query_params) if request.query_params else {},
        )
        if webhook_ev:
            webhook_ev.last_processing_error = "missing_secret"
            webhook_ev.processing_attempts = (webhook_ev.processing_attempts or 0) + 1
            try:
                db.commit()
            except Exception:
                db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura inválida")

    last_reason = None
    last_debug = None
    valid_signature = False
    matched_secret_index = None
    for idx, secret in enumerate(secrets):
        ok, reason, debug_info = verify_webhook_signature(
            secret, data, x_signature, x_request_id, data_id_from_query=data_id_query
        )
        last_reason = reason
        last_debug = debug_info
        if ok:
            valid_signature = True
            matched_secret_index = idx
            break

    if MP_WEBHOOK_DEBUG:
        log_struct(
            "mp_webhook_verify_result",
            level="info",
            request_id=getattr(request.state, "request_id", None),
            valid=valid_signature,
            reason=last_reason,
            secret_candidate_index=matched_secret_index,
            manifest_mode=last_debug.get("manifest_mode") if last_debug else None,
        )

    if not valid_signature:
        webhook_signature_invalid_total.labels(provider="mercadopago").inc()
        log_struct(
            "mp_webhook_fail",
            level="warning",
            request_id=getattr(request.state, "request_id", None),
            reason=last_reason or "digest_mismatch",
            data_id_query=data_id_query,
            has_x_signature=bool(x_signature and x_signature.strip()),
            has_x_request_id=bool(x_request_id and str(x_request_id).strip()),
            query_params=dict(request.query_params) if request.query_params else {},
            candidate_count=len(secrets),
            **(last_debug or {}),
        )
        if webhook_ev:
            webhook_ev.signature_valid = False
            webhook_ev.last_processing_error = last_reason or "digest_mismatch"
            webhook_ev.processing_attempts = (webhook_ev.processing_attempts or 0) + 1
            try:
                db.commit()
            except Exception:
                db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura inválida")

    if webhook_ev:
        webhook_ev.signature_valid = True

    if event_type != "payment":
        return {"status": "ok", "ignored": event_type}

    if payment_id is None:
        return {"status": "ok", "ignored": "no data.id"}

    webhook_received_total.labels(provider="mercadopago").inc()

    # Processamento assíncrono opcional (USE_WEBHOOK_ASYNC=true)
    if os.getenv("USE_WEBHOOK_ASYNC", "").strip().lower() == "true":
        try:
            db.commit()
            from app.worker.tasks import process_webhook_event_marketplace
            process_webhook_event_marketplace.delay(webhook_ev.id)
            webhook_queued_total.labels(provider="mercadopago").inc()
            return {"status": "ok", "queued": True}
        except Exception as e:
            log_error("USE_WEBHOOK_ASYNC: falha ao enfileirar webhook_ev.id=%s" % getattr(webhook_ev, "id"), exc_info=e)
            db.rollback()
            webhook_processing_error_total.labels(provider="mercadopago").inc()
            return {"status": "ok"}

    try:
        # Fase 2: tenta reconciliar pagamentos de vendas primeiro
        mp_payment = await _fetch_mp_payment_with_any_token(db, payment_id)
        if mp_payment:
            external_reference = str(mp_payment.get("external_reference") or "")
            tx = _find_transaction_for_mp_payment(db, external_reference, payment_id)
            if tx:
                mp_status = (mp_payment.get("status") or "").lower()
                pedido_ids_notify_hook: list[int] = []
                if tx.pedido_id or getattr(tx, "checkout_session_id", None):
                    from app.services.payments.webhook_marketplace_service import process_payment_notification

                    mp_pay_hook = process_payment_notification(db, tx, mp_status, mp_payment)
                    pedido_ids_notify_hook = mp_pay_hook.pedido_ids_notify_pagamento_confirmado
                else:
                    tx.status = _mp_status_to_internal(mp_status)
                    tx.provider_response = json.dumps(
                        {"idempotency_key": external_reference, "payment_details": mp_payment}
                    )
                    tx.provider_transaction_id = str(mp_payment.get("id") or tx.provider_transaction_id or "")
                    approved_at = _parse_datetime(mp_payment.get("date_approved"))
                    if approved_at:
                        tx.paid_at = approved_at
                    if tx.status in {"paid", "authorized"}:
                        tx.reconciliation_status = "matched"
                        tx.reconciliation_date = datetime.now(timezone.utc)
                    elif tx.status in {"failed", "cancelled"}:
                        tx.reconciliation_status = "divergence"
                        tx.reconciliation_date = datetime.now(timezone.utc)
                _sync_venda_pagamento_from_transaction(db, tx)
                webhook_ev.processed_at = datetime.now(timezone.utc)
                webhook_ev.processing_attempts = (webhook_ev.processing_attempts or 0) + 1
                webhook_ev.payment_transaction_id = tx.id
                webhook_ev.normalized_status = tx.status
                db.commit()
                if pedido_ids_notify_hook:
                    from app.services.payments.webhook_marketplace_service import (
                        dispatch_marketplace_pedido_pagamento_confirmado_notifications,
                    )

                    dispatch_marketplace_pedido_pagamento_confirmado_notifications(pedido_ids_notify_hook)
                webhook_processed_total.labels(provider="mercadopago").inc()
                is_mp = tx.pedido_id or getattr(tx, "checkout_session_id", None)
                return {"status": "ok", "kind": "marketplace" if is_mp else "venda_pagamento", "transaction_uuid": tx.uuid}

        # Mantém fluxo de billing já existente
        billing_service.process_payment_webhook(db, payment_id, raw_body=body.decode("utf-8", errors="replace")[:10000])
    except Exception as e:
        webhook_processing_error_total.labels(provider="mercadopago").inc()
        log_error("mercadopago webhook process_payment_webhook", exc_info=e)
        if webhook_ev:
            webhook_ev.processing_attempts = (webhook_ev.processing_attempts or 0) + 1
            webhook_ev.last_processing_error = str(e)[:2000]
            try:
                db.commit()
            except Exception:
                db.rollback()
        # Responder 200 para MP não reenviar em loop
    return {"status": "ok"}
