# PDV Ibix - Auditoria de pagamentos (marketplace)
"""Consultas técnicas/operacionais: transações, webhooks, estornos. Ação admin: estorno."""
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from app.core.middleware import require_superadmin
from app.database.connection import get_db
from app.models import (
    MarketplaceCheckoutSession,
    PaymentTransaction,
    PedidoMarketplace,
    Refund,
    Usuario,
    WebhookEvent,
)

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


class ReconcilePedidoMarketplaceBody(BaseModel):
    """Identifica o pedido marketplace; não altera status manualmente — só consulta o MP e aplica o retorno."""

    pedido_id: Optional[int] = None
    numero_pedido: Optional[str] = None
    loja_id: Optional[int] = None

    @model_validator(mode="after")
    def _exige_identificador(self) -> "ReconcilePedidoMarketplaceBody":
        has_pid = self.pedido_id is not None
        has_num = bool((self.numero_pedido or "").strip())
        if not has_pid and not has_num:
            raise ValueError("Informe pedido_id ou numero_pedido")
        return self


def _find_mp_transaction_for_pedido(db: Session, pedido: PedidoMarketplace) -> Optional[PaymentTransaction]:
    tid = (pedido.transaction_id or "").strip()
    if tid:
        tx = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.uuid == tid,
                PaymentTransaction.provider_code == "mercadopago",
            )
            .first()
        )
        if tx:
            return tx
    return (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.pedido_id == pedido.id,
            PaymentTransaction.provider_code == "mercadopago",
            PaymentTransaction.is_active.is_(True),
        )
        .order_by(PaymentTransaction.id.desc())
        .first()
    )


def _fetch_mp_payment_for_marketplace_tx(
    db: Session,
    tx: PaymentTransaction,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Retorna (corpo do pagamento MP, mensagem de erro de credencial)."""
    from app.services.payments.checkout_marketplace_service import _resolve_provider_and_credentials
    from app.services.payments.providers_marketplace import get_marketplace_provider

    try:
        _, _, credentials, _ = _resolve_provider_and_credentials(db, tx.cliente_id)
    except ValueError as e:
        return None, str(e)[:500]
    access_token = (
        credentials.get("access_token")
        or credentials.get("ACCESS_TOKEN")
        or credentials.get("token")
    )
    if not access_token:
        return None, "Token de acesso do Mercado Pago não configurado para este estabelecimento"

    provider = get_marketplace_provider("mercadopago")
    creds = {"access_token": access_token}

    if tx.provider_transaction_id:
        mp_payment = provider.fetch_payment(tx.provider_transaction_id, creds)
        if mp_payment:
            return mp_payment, None
    if tx.checkout_session_id:
        sess = (
            db.query(MarketplaceCheckoutSession)
            .filter(MarketplaceCheckoutSession.id == tx.checkout_session_id)
            .first()
        )
        if sess and (sess.uuid or "").strip():
            mp_payment = provider.search_payment_by_reference(f"mcs:{sess.uuid.strip()}", creds)
            if mp_payment:
                return mp_payment, None
    if tx.pedido_id:
        mp_payment = provider.search_payment_by_reference(str(tx.pedido_id), creds)
        if mp_payment:
            return mp_payment, None
    return None, None


def _repair_pedido_if_tx_already_paid(db: Session, pedido: PedidoMarketplace, tx: PaymentTransaction) -> bool:
    """
    Se a transação local já está paga/autorizada mas o pedido ainda não, alinha efeitos (ex.: falha parcial anterior).
    Checkout unificado: atualiza todos os pedidos da sessão.
    """
    st = (tx.status or "").lower()
    if st not in {"paid", "authorized"}:
        return False
    if (pedido.status_pagamento or "").strip().lower() == "pago":
        return False
    from app.services.payments.status_map import PAID
    from app.services.payments.webhook_marketplace_service import (
        _apply_single_pedido_paid,
        _process_session_payment_notification,
    )

    if tx.checkout_session_id:
        _process_session_payment_notification(db, tx, PAID, None)
    else:
        _apply_single_pedido_paid(db, tx, pedido.id)
    return True


@router.post("/reconciliar-pedido-marketplace")
async def reconciliar_pedido_marketplace_superadmin(
    body: ReconcilePedidoMarketplaceBody,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
) -> Dict[str, Any]:
    """
    Super Admin: consulta o Mercado Pago com as credenciais do estabelecimento e aplica o status ao pedido.
    Não é edição manual de status — apenas sincronização com o gateway (e reparo local se tx já paga).
    """
    from app.services.payments.webhook_marketplace_service import process_payment_notification

    if body.pedido_id is not None:
        pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == body.pedido_id).first()
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
    else:
        num = (body.numero_pedido or "").strip()
        q = db.query(PedidoMarketplace).filter(PedidoMarketplace.numero_pedido == num)
        if body.loja_id is not None:
            q = q.filter(PedidoMarketplace.loja_id == body.loja_id)
        rows = q.order_by(PedidoMarketplace.id.desc()).all()
        if not rows:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
        if len(rows) > 1:
            raise HTTPException(
                status_code=400,
                detail="Vários pedidos com esse número. Informe pedido_id ou loja_id para desambiguar.",
            )
        pedido = rows[0]

    tx = _find_mp_transaction_for_pedido(db, pedido)
    if not tx:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma transação Mercado Pago encontrada para este pedido",
        )

    if _repair_pedido_if_tx_already_paid(db, pedido, tx):
        db.commit()
        db.refresh(pedido)
        db.refresh(tx)
        return {
            "alterado": True,
            "message": "Pedido alinhado ao status já confirmado da transação local (reparo)",
            "pedido_id": pedido.id,
            "numero_pedido": pedido.numero_pedido,
            "transaction_uuid": tx.uuid,
            "transaction_status": tx.status,
            "provider_status": tx.provider_status,
            "pedido_status_pagamento": pedido.status_pagamento,
            "pedido_status_pedido": pedido.status_pedido,
        }

    mp_payment, cred_err = _fetch_mp_payment_for_marketplace_tx(db, tx)
    if cred_err:
        raise HTTPException(status_code=400, detail=cred_err)
    if not mp_payment:
        return {
            "alterado": False,
            "message": "Pagamento não encontrado no Mercado Pago (verifique credencial do estabelecimento e referência)",
            "pedido_id": pedido.id,
            "numero_pedido": pedido.numero_pedido,
            "transaction_uuid": tx.uuid,
            "transaction_status": tx.status,
            "pedido_status_pagamento": pedido.status_pagamento,
        }

    mp_status = (mp_payment.get("status") or "").lower()
    if mp_status == "pending":
        db.refresh(pedido)
        return {
            "alterado": False,
            "message": "Mercado Pago ainda retorna pagamento pendente ou em análise",
            "pedido_id": pedido.id,
            "numero_pedido": pedido.numero_pedido,
            "transaction_uuid": tx.uuid,
            "provider_status": mp_status,
            "transaction_status": tx.status,
            "pedido_status_pagamento": pedido.status_pagamento,
        }

    mp_res = process_payment_notification(db, tx, mp_status, mp_payment)
    if mp_res:
        db.commit()
        from app.services.payments.webhook_marketplace_service import (
            dispatch_marketplace_pedido_pagamento_confirmado_notifications,
        )

        dispatch_marketplace_pedido_pagamento_confirmado_notifications(
            mp_res.pedido_ids_notify_pagamento_confirmado
        )
        db.refresh(tx)
        db.refresh(pedido)
        return {
            "alterado": True,
            "message": "Status sincronizado com o Mercado Pago",
            "pedido_id": pedido.id,
            "numero_pedido": pedido.numero_pedido,
            "transaction_uuid": tx.uuid,
            "transaction_status": tx.status,
            "provider_status": mp_status,
            "pedido_status_pagamento": pedido.status_pagamento,
            "pedido_status_pedido": pedido.status_pedido,
        }

    db.rollback()
    db.refresh(tx)
    db.refresh(pedido)
    return {
        "alterado": False,
        "message": "Nenhuma alteração aplicável (regra de transição ou estado já reflete o gateway)",
        "pedido_id": pedido.id,
        "numero_pedido": pedido.numero_pedido,
        "transaction_uuid": tx.uuid,
        "transaction_status": tx.status,
        "provider_status": mp_status,
        "pedido_status_pagamento": pedido.status_pagamento,
    }
