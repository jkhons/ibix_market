# PDV Ibix - Auditoria de pagamentos (marketplace)
"""Consultas técnicas/operacionais: transações, webhooks, estornos. Ação admin: estorno."""
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.middleware import require_superadmin
from app.database.connection import get_db
from app.models import PaymentTransaction, Refund, Usuario, WebhookEvent

router = APIRouter(prefix="/admin/audit-pagamentos", tags=["Admin Audit Pagamentos"])


@router.get("/transacoes")
async def listar_transacoes_marketplace(
    db: Session = Depends(get_db),
    cliente_id: Optional[int] = Query(None),
    pedido_id: Optional[int] = Query(None),
    limit: int = Query(50, le=100),
    _: Usuario = Depends(require_superadmin()),
) -> Dict[str, Any]:
    """Lista transações de pagamento (marketplace: com pedido_id). Exige superadmin."""
    q = db.query(PaymentTransaction).filter(PaymentTransaction.pedido_id.isnot(None))
    if cliente_id is not None:
        q = q.filter(PaymentTransaction.cliente_id == cliente_id)
    if pedido_id is not None:
        q = q.filter(PaymentTransaction.pedido_id == pedido_id)
    rows = q.order_by(PaymentTransaction.id.desc()).limit(limit).all()
    return {
        "items": [
            {
                "id": t.id,
                "uuid": t.uuid,
                "cliente_id": t.cliente_id,
                "pedido_id": t.pedido_id,
                "provider_code": t.provider_code,
                "provider_transaction_id": t.provider_transaction_id,
                "status": t.status,
                "amount": float(t.amount) if t.amount else None,
                "attempt_number": t.attempt_number,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in rows
        ],
        "total": len(rows),
    }


@router.get("/webhooks")
async def listar_webhooks_recentes(
    db: Session = Depends(get_db),
    provider: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    _: Usuario = Depends(require_superadmin()),
) -> Dict[str, Any]:
    """Lista eventos de webhook recentes (auditoria). Exige superadmin."""
    q = db.query(WebhookEvent)
    if provider:
        q = q.filter(WebhookEvent.provider == provider)
    rows = q.order_by(WebhookEvent.id.desc()).limit(limit).all()
    return {
        "items": [
            {
                "id": w.id,
                "provider": w.provider,
                "event_type": w.event_type,
                "provider_event_id": w.provider_event_id,
                "payment_transaction_id": w.payment_transaction_id,
                "signature_valid": w.signature_valid,
                "processing_attempts": w.processing_attempts,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in rows
        ],
        "total": len(rows),
    }


@router.get("/refunds")
async def listar_refunds(
    db: Session = Depends(get_db),
    payment_transaction_id: Optional[int] = Query(None),
    limit: int = Query(50, le=100),
    _: Usuario = Depends(require_superadmin()),
) -> Dict[str, Any]:
    """Lista estornos registrados. Exige superadmin."""
    q = db.query(Refund)
    if payment_transaction_id is not None:
        q = q.filter(Refund.payment_transaction_id == payment_transaction_id)
    rows = q.order_by(Refund.id.desc()).limit(limit).all()
    return {
        "items": [
            {
                "id": r.id,
                "payment_transaction_id": r.payment_transaction_id,
                "provider_code": r.provider_code,
                "refund_type": r.refund_type,
                "amount": float(r.amount) if r.amount else None,
                "status": r.status,
                "requested_at": r.requested_at.isoformat() if r.requested_at else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


class RefundRequest(BaseModel):
    payment_transaction_id: int
    amount: Optional[Decimal] = None
    reason: Optional[str] = None


@router.post("/refund")
async def admin_request_refund(
    body: RefundRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
) -> Dict[str, Any]:
    """Ação administrativa: solicita estorno (total ou parcial). Exige superadmin."""
    from app.services.payments.refund_service import request_refund
    try:
        return request_refund(
            db,
            body.payment_transaction_id,
            amount=body.amount,
            reason=body.reason,
            requested_by_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)[:200])
