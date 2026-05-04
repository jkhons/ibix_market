# PDV Ibix - Checkout marketplace (gateway + tentativa)
"""Gera checkout no provedor e persiste PaymentTransaction; estoque é baixado no webhook de pagamento."""
import json
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import (
    Empresa,
    LojaMarketplace,
    MarketplaceCheckoutSession,
    MarketplaceCheckoutSessionPedido,
    PaymentTransaction,
    PedidoItemMarketplace,
    PedidoMarketplace,
)
from app.services.payments.base import PaymentProviderBase
from app.services.payments.credentials import decrypt_credentials
from app.services.payments.factory import get_provider_for_cliente
from app.services.payments.providers_marketplace import get_marketplace_provider
from app.services.payments.mercadopago_api import minutes_until_mp_expiration
from app.services.payments.status_map import PENDING
from .base import CheckoutResult

PROVIDER_MP = "mercadopago"


def _marketplace_payer_info(
    comprador_nome: Optional[str],
    comprador_email: Optional[str],
    comprador_documento: Optional[str],
) -> Dict[str, Any]:
    """Dados do pagador para Preferência MP; document → payer.identification (CPF/CNPJ)."""
    nome_c = (comprador_nome or "").strip()
    partes = nome_c.split(None, 1) if nome_c else []
    info: Dict[str, Any] = {
        "first_name": partes[0] if partes else nome_c,
        "last_name": partes[1] if len(partes) > 1 else "",
        "email": (comprador_email or "").strip(),
    }
    doc = (comprador_documento or "").strip()
    if doc:
        info["document"] = doc[:32]
    return info


def _transaction_provider_response_json(result: CheckoutResult, external_reference: str) -> str:
    """Snapshot em payment_transactions.provider_response (idempotência / diagnóstico)."""
    return json.dumps(
        {
            "external_reference": external_reference,
            "redirect_url": result.redirect_url,
            "checkout_type": result.checkout_type,
            "qr_code": result.qr_code,
            "copy_paste_code": result.copy_paste_code,
            "qr_code_base64": result.qr_code_base64,
            "expires_at": result.expires_at,
        }
    )


def _checkout_gateway_public_dict(result: CheckoutResult) -> Dict[str, Any]:
    """Campos comuns da resposta HTTP (web + app): inclui objeto pix para contrato mobile."""
    out: Dict[str, Any] = {
        "redirect_url": result.redirect_url,
        "provider": result.provider,
        "checkout_type": result.checkout_type,
        "payment_method": result.payment_method,
        "qr_code": result.qr_code,
        "copy_paste_code": result.copy_paste_code,
    }
    copia = (result.copy_paste_code or result.qr_code or "").strip()
    if result.checkout_type == "pix" and copia:
        out["pix"] = {
            "copia_cola": copia,
            "qr_code": result.qr_code or copia,
            "qr_code_base64": result.qr_code_base64,
            "expiracao_minutos": minutes_until_mp_expiration(result.expires_at),
        }
    return out


def _resolve_provider_and_credentials(
    db: Session, cliente_id: int
) -> Tuple[str, PaymentProviderBase, Dict[str, Any], str]:
    """
    Define provedor e credenciais para o checkout da loja.
    Se a empresa fiscal do CA estiver em modo "plataforma" (plataforma recebe e repassa),
    usa as credenciais da plataforma (Admin Billing). Caso contrário, usa a config do CA em Recebíveis.
    Retorna (provider_code, provider, credentials, modo_recebimento).
    """
    empresa = (
        db.query(Empresa)
        .filter(Empresa.cliente_id == cliente_id, Empresa.ativo.is_(True))
        .first()
    )
    modo = (empresa.modo_recebimento or "").strip().lower() if empresa else ""
    if modo == "plataforma":
        gw = (getattr(empresa, "gateway_plataforma", None) or "mercadopago").strip().lower()
        if gw == "mercadopago":
            from app.core.billing_config import get_mp_access_token

            access_token = get_mp_access_token(db)
            if not access_token:
                raise ValueError(
                    "Modo plataforma com Mercado Pago exige access_token em Admin Billing (billing_mp_access_token)."
                )
            provider = get_marketplace_provider(PROVIDER_MP)
            return (PROVIDER_MP, provider, {"access_token": access_token}, "plataforma")
        if gw == "pagbank":
            from app.core.billing_config import get_plataforma_pagbank_access_token
            from app.core.pagbank_config import is_pagbank_sandbox
            from app.services.payments.providers_marketplace import PagBankMarketplaceProvider

            token = get_plataforma_pagbank_access_token(db)
            if not token:
                raise ValueError(
                    "Modo plataforma com PagBank exige token da plataforma: billing_plataforma_pagbank_access_token "
                    "em Admin Billing ou variável PLATAFORMA_PAGBANK_ACCESS_TOKEN."
                )
            provider = PagBankMarketplaceProvider(webhook_secret=None)
            creds = {"access_token": token, "sandbox": is_pagbank_sandbox(db)}
            return ("pagbank", provider, creds, "plataforma")
        if gw == "pagarme":
            from app.core.billing_config import get_plataforma_pagarme_secret_key
            from app.services.payments.providers_marketplace import PagarMeMarketplaceProvider

            sk = get_plataforma_pagarme_secret_key(db)
            if not sk:
                raise ValueError(
                    "Modo plataforma com Pagar.me exige billing_plataforma_pagarme_secret_key em Admin Billing "
                    "ou variável PLATAFORMA_PAGARME_SECRET_KEY."
                )
            provider = PagarMeMarketplaceProvider(webhook_secret=None)
            return ("pagarme", provider, {"secret_key": sk}, "plataforma")
        raise ValueError(
            f"Gateway de plataforma inválido: {gw}. Use mercadopago, pagbank ou pagarme (definido em Fiscal > Empresa)."
        )

    config, provider = get_provider_for_cliente(db, cliente_id)
    if not config or not provider:
        raise ValueError(
            "Nenhum gateway de pagamento ativo configurado para este estabelecimento."
        )
    credentials = decrypt_credentials(config.credentials_encrypted) or {}
    modo_final = modo if modo == "direto" else "plataforma"
    return (config.provider_code, provider, credentials, modo_final)


def create_checkout_for_pedido(
    db: Session,
    pedido_id: int,
    payment_method: str,
    *,
    back_url_success: Optional[str] = None,
    back_url_cancel: Optional[str] = None,
    notification_url: Optional[str] = None,
    base_url: Optional[str] = None,
    reserve_minutes: int = 30,
) -> Dict[str, Any]:
    """
    Obtém provedor ativo, cria checkout no gateway e persiste a primeira tentativa (PaymentTransaction).
    Estoque só é baixado quando o pagamento for confirmado (webhook). Retorna dict com redirect_url, etc.
    """
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not pedido:
        raise ValueError("Pedido não encontrado")
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == pedido.loja_id).first()
    if not loja:
        raise ValueError("Loja não encontrada")
    cliente_id = pedido.tenant_id
    provider_code, provider, credentials, modo_recebimento = _resolve_provider_and_credentials(db, cliente_id)
    method = (payment_method or "pix").lower()
    if not provider.supports_method(method):
        raise ValueError(f"Método '{payment_method}' não suportado pelo gateway.")
    total = pedido.total
    if total is None or float(total) <= 0:
        raise ValueError("Total do pedido inválido.")
    external_reference = str(pedido_id)
    back_urls = {}
    if back_url_success:
        back_urls["success"] = back_url_success
    if back_url_cancel:
        back_urls["failure"] = back_url_cancel
    kwargs: Dict[str, Any] = {}
    if back_urls:
        kwargs["back_urls"] = back_urls
    if base_url:
        if provider_code == "mercadopago":
            kwargs["notification_url"] = f"{base_url.rstrip('/')}/api/webhooks/mercadopago?source_news=webhooks"
        elif provider_code == "pagbank":
            kwargs["notification_url"] = f"{base_url.rstrip('/')}/api/v1/payments/webhook/pagbank"
        elif provider_code == "pagarme":
            kwargs["notification_url"] = f"{base_url.rstrip('/')}/api/v1/payments/webhook/pagarme"
        else:
            kwargs["notification_url"] = notification_url
    elif notification_url:
        kwargs["notification_url"] = notification_url

    itens_pedido = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == pedido_id).all()
    if itens_pedido:
        kwargs["items_detail"] = [
            {
                "id": str(it.anuncio_id),
                "title": (it.nome_produto_snapshot or "Produto")[:256],
                "description": (it.nome_produto_snapshot or "Produto Marketplace")[:256],
                "category_id": (it.categoria_snapshot or "others")[:256],
                "quantity": it.quantidade,
                "unit_price": float(it.preco_unitario),
            }
            for it in itens_pedido
        ]

    kwargs["payer_info"] = _marketplace_payer_info(
        pedido.comprador_nome,
        pedido.comprador_email,
        pedido.comprador_documento,
    )
    if provider_code == "mercadopago" and method == "pix":
        kwargs["mp_idempotency_key"] = str(uuid.uuid4())

    result: CheckoutResult = provider.create_checkout(
        amount=Decimal(str(total)),
        payment_method=method,
        external_reference=external_reference,
        credentials=credentials,
        **kwargs,
    )
    transaction_uuid = str(uuid.uuid4())
    attempt_number = 1
    # Contexto único (Bloco 0): marketplace = apenas pedido_id; venda_id/caixa_id nulos
    tx = PaymentTransaction(
        uuid=transaction_uuid,
        cliente_id=cliente_id,
        venda_id=None,
        caixa_id=None,
        pedido_id=pedido_id,
        provider_code=provider_code,
        provider_checkout_id=result.provider_checkout_id,
        provider_transaction_id=result.provider_payment_id,
        provider_status="pending",
        payment_method=method,
        amount=Decimal(str(total)),
        status=PENDING,
        attempt_number=attempt_number,
        is_active=True,
        reconciliation_status="pending",
        modo_recebimento=modo_recebimento,
        repasse_status_id=1 if modo_recebimento == "plataforma" else None,
        provider_response=_transaction_provider_response_json(result, external_reference),
    )
    db.add(tx)
    db.flush()
    pedido.gateway_pagamento = provider_code
    pedido.transaction_id = transaction_uuid
    db.commit()
    db.refresh(tx)
    pub = _checkout_gateway_public_dict(result)
    return {
        **pub,
        "pedido_id": pedido_id,
        "numero_pedido": pedido.numero_pedido,
        "transaction_uuid": transaction_uuid,
    }


def create_checkout_for_session(
    db: Session,
    checkout_session_id: int,
    session_uuid: str,
    pedido_ids: List[int],
    payment_method: str,
    *,
    back_url_success: Optional[str] = None,
    back_url_cancel: Optional[str] = None,
    notification_url: Optional[str] = None,
    base_url: Optional[str] = None,
    reserve_minutes: int = 30,
) -> Dict[str, Any]:
    """
    Um pagamento no gateway para N pedidos (checkout unificado). external_reference = mcs:{uuid}.
    Transação aponta para checkout_session_id e pedido âncora (primeiro id). Baixa de estoque no webhook.
    """
    if not pedido_ids:
        raise ValueError("Nenhum pedido na sessão")
    pedidos = (
        db.query(PedidoMarketplace)
        .filter(PedidoMarketplace.id.in_(pedido_ids))
        .order_by(PedidoMarketplace.id.asc())
        .all()
    )
    if len(pedidos) != len(pedido_ids):
        raise ValueError("Pedido não encontrado")
    anchor = pedidos[0]
    cliente_id = anchor.tenant_id
    total_agregado = sum(Decimal(str(p.total or 0)) for p in pedidos)
    if total_agregado <= 0:
        raise ValueError("Total da sessão inválido")
    provider_code, provider, credentials, modo_recebimento = _resolve_provider_and_credentials(db, cliente_id)
    method = (payment_method or "pix").lower()
    if not provider.supports_method(method):
        raise ValueError(f"Método '{payment_method}' não suportado pelo gateway.")
    external_reference = f"mcs:{session_uuid}"
    back_urls = {}
    if back_url_success:
        back_urls["success"] = back_url_success
    if back_url_cancel:
        back_urls["failure"] = back_url_cancel
    kwargs: Dict[str, Any] = {}
    if back_urls:
        kwargs["back_urls"] = back_urls
    if base_url:
        if provider_code == "mercadopago":
            kwargs["notification_url"] = f"{base_url.rstrip('/')}/api/webhooks/mercadopago?source_news=webhooks"
        elif provider_code == "pagbank":
            kwargs["notification_url"] = f"{base_url.rstrip('/')}/api/v1/payments/webhook/pagbank"
        elif provider_code == "pagarme":
            kwargs["notification_url"] = f"{base_url.rstrip('/')}/api/v1/payments/webhook/pagarme"
        else:
            kwargs["notification_url"] = notification_url
    elif notification_url:
        kwargs["notification_url"] = notification_url

    items_detail: list[Dict[str, Any]] = []
    for p in pedidos:
        itens_pedido = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == p.id).all()
        for it in itens_pedido:
            items_detail.append(
                {
                    "id": str(it.anuncio_id),
                    "title": (it.nome_produto_snapshot or "Produto")[:256],
                    "description": (it.nome_produto_snapshot or "Produto Marketplace")[:256],
                    "category_id": (it.categoria_snapshot or "others")[:256],
                    "quantity": it.quantidade,
                    "unit_price": float(it.preco_unitario),
                }
            )
    if items_detail:
        kwargs["items_detail"] = items_detail

    kwargs["payer_info"] = _marketplace_payer_info(
        anchor.comprador_nome,
        anchor.comprador_email,
        anchor.comprador_documento,
    )
    if provider_code == "mercadopago" and method == "pix":
        kwargs["mp_idempotency_key"] = str(uuid.uuid4())

    result: CheckoutResult = provider.create_checkout(
        amount=Decimal(str(total_agregado)),
        payment_method=method,
        external_reference=external_reference,
        credentials=credentials,
        **kwargs,
    )
    transaction_uuid = str(uuid.uuid4())
    tx = PaymentTransaction(
        uuid=transaction_uuid,
        cliente_id=cliente_id,
        venda_id=None,
        caixa_id=None,
        pedido_id=anchor.id,
        checkout_session_id=checkout_session_id,
        provider_code=provider_code,
        provider_checkout_id=result.provider_checkout_id,
        provider_transaction_id=result.provider_payment_id,
        provider_status="pending",
        payment_method=method,
        amount=Decimal(str(total_agregado)),
        status=PENDING,
        attempt_number=1,
        is_active=True,
        reconciliation_status="pending",
        modo_recebimento=modo_recebimento,
        repasse_status_id=1 if modo_recebimento == "plataforma" else None,
        provider_response=_transaction_provider_response_json(result, external_reference),
    )
    db.add(tx)
    db.flush()
    sess = db.query(MarketplaceCheckoutSession).filter(MarketplaceCheckoutSession.id == checkout_session_id).first()
    if sess:
        sess.total_agregado = total_agregado
    for p in pedidos:
        p.gateway_pagamento = provider_code
        p.transaction_id = transaction_uuid
    db.commit()
    db.refresh(tx)
    pub = _checkout_gateway_public_dict(result)
    return {
        **pub,
        "pedido_id": anchor.id,
        "numero_pedido": anchor.numero_pedido,
        "transaction_uuid": transaction_uuid,
    }


def create_retry_checkout_for_session(
    db: Session,
    session_uuid: str,
    payment_method: str,
    *,
    back_url_success: Optional[str] = None,
    back_url_cancel: Optional[str] = None,
    notification_url: Optional[str] = None,
    base_url: Optional[str] = None,
    reserve_minutes: int = 30,
) -> Dict[str, Any]:
    """
    Nova tentativa para checkout unificado (N pedidos / external_reference mcs:{uuid}).
    Desativa transações anteriores da sessão e cria novo checkout agregado no gateway.
    """
    from sqlalchemy import func

    uuid_clean = (session_uuid or "").strip()
    if not uuid_clean:
        raise ValueError("Sessão inválida")
    sess = db.query(MarketplaceCheckoutSession).filter(MarketplaceCheckoutSession.uuid == uuid_clean).first()
    if not sess:
        raise ValueError("Sessão não encontrada")
    if (sess.status or "").strip().lower() == "pago":
        raise ValueError("Esta sessão já foi paga")
    links = (
        db.query(MarketplaceCheckoutSessionPedido)
        .filter(MarketplaceCheckoutSessionPedido.session_id == sess.id)
        .order_by(MarketplaceCheckoutSessionPedido.sort_order.asc())
        .all()
    )
    if not links:
        raise ValueError("Sessão sem pedidos")
    pedido_ids = [link.pedido_id for link in links]
    pedidos_rows = (
        db.query(PedidoMarketplace).filter(PedidoMarketplace.id.in_(pedido_ids)).all()
    )
    if len(pedidos_rows) != len(pedido_ids):
        raise ValueError("Pedido não encontrado")
    by_id = {p.id: p for p in pedidos_rows}
    pedidos = [by_id[pid] for pid in pedido_ids if pid in by_id]
    if len(pedidos) != len(pedido_ids):
        raise ValueError("Pedido não encontrado")
    for p in pedidos:
        if (p.status_pagamento or "").strip().lower() == "pago":
            raise ValueError("Um ou mais pedidos já estão pagos")
    max_attempt = (
        db.query(func.coalesce(func.max(PaymentTransaction.attempt_number), 0))
        .filter(PaymentTransaction.checkout_session_id == sess.id)
        .scalar()
    )
    attempt_number = int(max_attempt or 0) + 1
    db.query(PaymentTransaction).filter(PaymentTransaction.checkout_session_id == sess.id).update(
        {PaymentTransaction.is_active: False}, synchronize_session="fetch"
    )
    anchor = pedidos[0]
    cliente_id = anchor.tenant_id
    total_agregado = sum(Decimal(str(p.total or 0)) for p in pedidos)
    if total_agregado <= 0:
        raise ValueError("Total da sessão inválido")
    provider_code, provider, credentials, modo_recebimento = _resolve_provider_and_credentials(db, cliente_id)
    method = (payment_method or "pix").lower()
    if not provider.supports_method(method):
        raise ValueError(f"Método '{payment_method}' não suportado pelo gateway.")
    external_reference = f"mcs:{uuid_clean}"
    back_urls = {}
    if back_url_success:
        back_urls["success"] = back_url_success
    if back_url_cancel:
        back_urls["failure"] = back_url_cancel
    kwargs: Dict[str, Any] = {}
    if back_urls:
        kwargs["back_urls"] = back_urls
    if base_url:
        if provider_code == "mercadopago":
            kwargs["notification_url"] = f"{base_url.rstrip('/')}/api/webhooks/mercadopago?source_news=webhooks"
        elif provider_code == "pagbank":
            kwargs["notification_url"] = f"{base_url.rstrip('/')}/api/v1/payments/webhook/pagbank"
        elif provider_code == "pagarme":
            kwargs["notification_url"] = f"{base_url.rstrip('/')}/api/v1/payments/webhook/pagarme"
        else:
            kwargs["notification_url"] = notification_url
    elif notification_url:
        kwargs["notification_url"] = notification_url
    items_detail: list[Dict[str, Any]] = []
    for p in pedidos:
        itens_pedido = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == p.id).all()
        for it in itens_pedido:
            items_detail.append(
                {
                    "id": str(it.anuncio_id),
                    "title": (it.nome_produto_snapshot or "Produto")[:256],
                    "description": (it.nome_produto_snapshot or "Produto Marketplace")[:256],
                    "category_id": (it.categoria_snapshot or "others")[:256],
                    "quantity": it.quantidade,
                    "unit_price": float(it.preco_unitario),
                }
            )
    if items_detail:
        kwargs["items_detail"] = items_detail
    kwargs["payer_info"] = _marketplace_payer_info(
        anchor.comprador_nome,
        anchor.comprador_email,
        anchor.comprador_documento,
    )
    if provider_code == "mercadopago" and method == "pix":
        kwargs["mp_idempotency_key"] = str(uuid.uuid4())
    result: CheckoutResult = provider.create_checkout(
        amount=Decimal(str(total_agregado)),
        payment_method=method,
        external_reference=external_reference,
        credentials=credentials,
        **kwargs,
    )
    transaction_uuid = str(uuid.uuid4())
    tx = PaymentTransaction(
        uuid=transaction_uuid,
        cliente_id=cliente_id,
        venda_id=None,
        caixa_id=None,
        pedido_id=anchor.id,
        checkout_session_id=sess.id,
        provider_code=provider_code,
        provider_checkout_id=result.provider_checkout_id,
        provider_transaction_id=result.provider_payment_id,
        provider_status="pending",
        payment_method=method,
        amount=Decimal(str(total_agregado)),
        status=PENDING,
        attempt_number=attempt_number,
        is_active=True,
        reconciliation_status="pending",
        modo_recebimento=modo_recebimento,
        repasse_status_id=1 if modo_recebimento == "plataforma" else None,
        provider_response=_transaction_provider_response_json(result, external_reference),
    )
    db.add(tx)
    db.flush()
    sess.status = "pendente"
    sess.total_agregado = total_agregado
    for p in pedidos:
        p.gateway_pagamento = provider_code
        p.transaction_id = transaction_uuid
    db.commit()
    db.refresh(tx)
    pub = _checkout_gateway_public_dict(result)
    return {
        **pub,
        "pedido_id": anchor.id,
        "numero_pedido": anchor.numero_pedido,
        "transaction_uuid": transaction_uuid,
    }


def create_retry_checkout_for_pedido(
    db: Session,
    pedido_id: int,
    payment_method: str,
    *,
    back_url_success: Optional[str] = None,
    back_url_cancel: Optional[str] = None,
    notification_url: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Nova tentativa de pagamento: desativa tentativas anteriores (is_active=False),
    cria novo checkout no gateway e nova PaymentTransaction com attempt_number incrementado.
    Não cria nova reserva (já existente no pedido).
    """
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not pedido:
        raise ValueError("Pedido não encontrado")
    provider_code, provider, credentials, modo_recebimento = _resolve_provider_and_credentials(db, pedido.tenant_id)
    method = (payment_method or "pix").lower()
    if not provider.supports_method(method):
        raise ValueError(f"Método '{payment_method}' não suportado.")
    total = pedido.total
    if total is None or float(total) <= 0:
        raise ValueError("Total do pedido inválido.")
    from sqlalchemy import func
    max_attempt = (
        db.query(func.coalesce(func.max(PaymentTransaction.attempt_number), 0))
        .filter(PaymentTransaction.pedido_id == pedido_id)
        .scalar()
    )
    attempt_number = int(max_attempt or 0) + 1
    db.query(PaymentTransaction).filter(PaymentTransaction.pedido_id == pedido_id).update(
        {PaymentTransaction.is_active: False}, synchronize_session="fetch"
    )
    external_reference = str(pedido_id)
    kwargs: Dict[str, Any] = {}
    if back_url_success or back_url_cancel:
        kwargs["back_urls"] = {
            k: v for k, v in (("success", back_url_success), ("failure", back_url_cancel)) if v
        }
    if base_url:
        if provider_code == "mercadopago":
            kwargs["notification_url"] = f"{base_url.rstrip('/')}/api/webhooks/mercadopago?source_news=webhooks"
        elif provider_code == "pagbank":
            kwargs["notification_url"] = f"{base_url.rstrip('/')}/api/v1/payments/webhook/pagbank"
        elif provider_code == "pagarme":
            kwargs["notification_url"] = f"{base_url.rstrip('/')}/api/v1/payments/webhook/pagarme"
        else:
            kwargs["notification_url"] = notification_url
    elif notification_url:
        kwargs["notification_url"] = notification_url

    itens_pedido = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == pedido_id).all()
    if itens_pedido:
        kwargs["items_detail"] = [
            {
                "id": str(it.anuncio_id),
                "title": (it.nome_produto_snapshot or "Produto")[:256],
                "description": (it.nome_produto_snapshot or "Produto Marketplace")[:256],
                "category_id": (it.categoria_snapshot or "others")[:256],
                "quantity": it.quantidade,
                "unit_price": float(it.preco_unitario),
            }
            for it in itens_pedido
        ]

    kwargs["payer_info"] = _marketplace_payer_info(
        pedido.comprador_nome,
        pedido.comprador_email,
        pedido.comprador_documento,
    )
    if provider_code == "mercadopago" and method == "pix":
        kwargs["mp_idempotency_key"] = str(uuid.uuid4())

    result: CheckoutResult = provider.create_checkout(
        amount=Decimal(str(total)),
        payment_method=method,
        external_reference=external_reference,
        credentials=credentials,
        **kwargs,
    )
    transaction_uuid = str(uuid.uuid4())
    tx = PaymentTransaction(
        uuid=transaction_uuid,
        cliente_id=pedido.tenant_id,
        venda_id=None,
        caixa_id=None,
        pedido_id=pedido_id,
        provider_code=provider_code,
        provider_checkout_id=result.provider_checkout_id,
        provider_transaction_id=result.provider_payment_id,
        provider_status="pending",
        payment_method=method,
        amount=Decimal(str(total)),
        status=PENDING,
        attempt_number=attempt_number,
        is_active=True,
        reconciliation_status="pending",
        modo_recebimento=modo_recebimento,
        repasse_status_id=1 if modo_recebimento == "plataforma" else None,
        provider_response=_transaction_provider_response_json(result, external_reference),
    )
    db.add(tx)
    db.flush()
    pedido.gateway_pagamento = provider_code
    pedido.transaction_id = transaction_uuid
    db.commit()
    db.refresh(tx)
    pub = _checkout_gateway_public_dict(result)
    return {
        **pub,
        "pedido_id": pedido_id,
        "numero_pedido": pedido.numero_pedido,
        "transaction_uuid": transaction_uuid,
    }
