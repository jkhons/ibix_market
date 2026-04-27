# PDV Ibix - Router central de webhooks de pagamento (F2)
# Rotas: /api/webhooks/payments/{provider} — Mercado Pago delegado; PagBank/Pagar.me espelham lógica de /api/v1/payments/webhook.
import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.rate_limiter import check_webhook_rate_limit
from app.database.connection import get_db

router = APIRouter(prefix="/payments", tags=["Webhooks Payments"])


@router.post("/mercadopago")
async def payments_mercadopago(
    request: Request,
    db: Session = Depends(get_db),
    x_signature: Optional[str] = Header(None, alias="x-signature"),
    x_request_id: Optional[str] = Header(None, alias="x-request-id"),
    _: None = Depends(check_webhook_rate_limit),
):
    """Delega para o handler do Mercado Pago (mesma lógica de /api/webhooks/mercadopago)."""
    from app.api.webhooks_mercadopago import mercadopago_webhook
    return await mercadopago_webhook(request, db, x_signature, x_request_id)


@router.post("/asaas")
async def payments_asaas(
    request: Request,
    _: None = Depends(check_webhook_rate_limit),
):
    """Stub: integração Asaas não implementada em V1."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Webhook Asaas não implementado"},
    )


@router.post("/pagbank")
async def payments_pagbank(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(check_webhook_rate_limit),
):
    """Mesmo processamento de POST /api/v1/payments/webhook/pagbank (URL alternativa)."""
    from app.services.payments.webhook_provider_sync import apply_provider_webhook

    body = await request.body()
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"detail": "JSON inválido"})
    return apply_provider_webhook(db, "pagbank", payload)


@router.post("/pagarme")
async def payments_pagarme(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(check_webhook_rate_limit),
):
    """Mesmo processamento de POST /api/v1/payments/webhook/pagarme (URL alternativa)."""
    from app.services.payments.webhook_provider_sync import apply_provider_webhook

    body = await request.body()
    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"detail": "JSON inválido"})
    return apply_provider_webhook(db, "pagarme", payload)


@router.post("/stripe")
async def payments_stripe(
    request: Request,
    _: None = Depends(check_webhook_rate_limit),
):
    """Stub: integração Stripe não implementada em V1."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Webhook Stripe não implementado"},
    )
