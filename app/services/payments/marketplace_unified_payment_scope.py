# PDV Ibix — escopo RBAC e rateio por tenant em checkout marketplace unificado (1 pagamento, N pedidos).
from decimal import Decimal
from typing import Optional, Sequence, Tuple, List

from sqlalchemy import and_, exists, or_
from sqlalchemy.orm import Session

from app.models import (
    MarketplaceCheckoutSessionPedido,
    PaymentTransaction,
    PedidoMarketplace,
)


def participant_tenant_in_session_exists(estabelecimento_id: int):
    """EXISTS correlacionado: a sessão do pagamento inclui pedido do tenant."""
    return exists().where(
        MarketplaceCheckoutSessionPedido.session_id == PaymentTransaction.checkout_session_id,
        PedidoMarketplace.id == MarketplaceCheckoutSessionPedido.pedido_id,
        PedidoMarketplace.tenant_id == estabelecimento_id,
    )


def filter_transactions_query_for_estabelecimento(query, estabelecimento_id: int):
    """Transação “dela” pelo cliente_id OU por pedido na sessão unificada (mesmo tenant)."""
    return query.filter(
        or_(
            PaymentTransaction.cliente_id == estabelecimento_id,
            and_(
                PaymentTransaction.checkout_session_id.isnot(None),
                participant_tenant_in_session_exists(estabelecimento_id),
            ),
        )
    )


def filter_transactions_query_for_allowed_clientes(query, allowed_ids: Sequence[int]):
    if not allowed_ids:
        return query.filter(False)
    ids = list(allowed_ids)
    return query.filter(
        or_(
            PaymentTransaction.cliente_id.in_(ids),
            and_(
                PaymentTransaction.checkout_session_id.isnot(None),
                exists().where(
                    MarketplaceCheckoutSessionPedido.session_id == PaymentTransaction.checkout_session_id,
                    PedidoMarketplace.id == MarketplaceCheckoutSessionPedido.pedido_id,
                    PedidoMarketplace.tenant_id.in_(ids),
                ),
            ),
        )
    )


def usuario_pode_acessar_transacao_pagamento(
    db: Session,
    tx: PaymentTransaction,
    allowed_cliente_ids: Optional[List[int]],
) -> bool:
    if allowed_cliente_ids is None:
        return True
    if tx.cliente_id in allowed_cliente_ids:
        return True
    if not tx.checkout_session_id:
        return False
    q = (
        db.query(PedidoMarketplace.id)
        .join(
            MarketplaceCheckoutSessionPedido,
            MarketplaceCheckoutSessionPedido.pedido_id == PedidoMarketplace.id,
        )
        .filter(
            MarketplaceCheckoutSessionPedido.session_id == tx.checkout_session_id,
            PedidoMarketplace.tenant_id.in_(allowed_cliente_ids),
        )
    )
    return q.first() is not None


def listagem_sessao_valores_para_tenant(
    db: Session,
    *,
    checkout_session_id: int,
    viewer_tenant_id: int,
) -> Tuple[Decimal, Optional[str], Optional[int]]:
    """Soma totais dos pedidos da sessão do tenant + referência para listagem."""
    rows = (
        db.query(
            PedidoMarketplace.total,
            PedidoMarketplace.numero_pedido,
            PedidoMarketplace.id,
        )
        .join(
            MarketplaceCheckoutSessionPedido,
            MarketplaceCheckoutSessionPedido.pedido_id == PedidoMarketplace.id,
        )
        .filter(
            MarketplaceCheckoutSessionPedido.session_id == checkout_session_id,
            PedidoMarketplace.tenant_id == viewer_tenant_id,
        )
        .order_by(MarketplaceCheckoutSessionPedido.sort_order.asc())
        .all()
    )
    if not rows:
        return Decimal("0"), None, None
    total = Decimal("0")
    for t, _, _ in rows:
        total += Decimal(str(t or 0))
    nums = [n for _, n, _ in rows if n]
    ref = ", ".join(str(x) for x in nums) if nums else None
    pid = rows[0][2]
    return total, ref, pid


def amount_payment_transaction_para_estabelecimento(
    db: Session,
    tx: PaymentTransaction,
    estabelecimento_id: int,
) -> Decimal:
    """Valor atribuível ao tenant em transações de sessão unificada; senão valor integral da linha."""
    if not tx.checkout_session_id:
        return Decimal(str(tx.amount or 0))
    amt, _, _ = listagem_sessao_valores_para_tenant(
        db,
        checkout_session_id=tx.checkout_session_id,
        viewer_tenant_id=estabelecimento_id,
    )
    return amt


def overrides_listagem_transacao_para_tenant(
    db: Session,
    tx: PaymentTransaction,
    viewer_tenant_id: Optional[int],
) -> Tuple[Optional[int], Decimal, Optional[str], Optional[int]]:
    """
    (cliente_id exibido, amount, numero_pedido, pedido_id) para lista Recebíveis.
    viewer_tenant_id None = contexto todos: mantém valores da linha física da transação.
    """
    if viewer_tenant_id is None:
        pedido_label = tx.pedido.numero_pedido if tx.pedido else None
        return None, Decimal(str(tx.amount or 0)), pedido_label, tx.pedido_id
    if not tx.checkout_session_id:
        return (
            viewer_tenant_id,
            Decimal(str(tx.amount or 0)),
            tx.pedido.numero_pedido if tx.pedido else None,
            tx.pedido_id,
        )
    amt, ref, pid = listagem_sessao_valores_para_tenant(
        db, checkout_session_id=tx.checkout_session_id, viewer_tenant_id=viewer_tenant_id
    )
    return viewer_tenant_id, amt, ref, pid
