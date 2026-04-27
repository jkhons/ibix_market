# PDV Ibix - API Módulo de Pagamentos (Fase 3.3)
"""Configs por estabelecimento (credenciais criptografadas); process via Orquestrador; status; webhook."""
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from ...core.payment_gateway_policy import (
    HTTP_DETAIL_GATEWAY_SELF_SERVICE_DENIED,
    user_may_mutate_establishment_gateway,
)
from ...core.rate_limiter import check_webhook_rate_limit
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models import PaymentProviderConfig, PaymentTransaction, Usuario
from ...models.empresa import Empresa
from ...schemas.payment import (
    PaymentProcessRequest,
    PaymentProcessResponse,
    PaymentProviderConfigCreate,
    PaymentProviderConfigResponse,
    PaymentProviderConfigUpdate,
    PaymentStatusResponse,
    PaymentTransactionListItem,
)
from ...services.payments import PaymentOrchestrator, encrypt_credentials

router = APIRouter(prefix="/payments", tags=["Pagamentos (módulo 3.3)"])
ALLOWED_PROVIDERS = {"mercadopago", "pagbank", "pagarme"}


def _normalize_method(method: str) -> str:
    raw = (method or "").strip().lower()
    mapping = {
        "cartao_credito": "credit",
        "cartao_debito": "debit",
        "credito": "credit",
        "debito": "debit",
        "transferencia": "transfer",
        "dinheiro": "cash",
    }
    return mapping.get(raw, raw)


def _allowed_cliente_ids(scope: ClienteScope) -> Optional[List[int]]:
    if not scope.must_filter_by_cliente():
        return None
    return scope.allowed_ids or []


@router.get("/modo-recebimento")
async def modo_recebimento(
    cliente_id: int = Query(..., alias="clienteId"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Retorna o modo_recebimento da empresa fiscal vinculada ao cliente."""
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Fora do escopo")
    emp = db.query(Empresa).filter(Empresa.cliente_id == cliente_id, Empresa.ativo.is_(True)).first()
    modo = (emp.modo_recebimento if emp else "plataforma") or "plataforma"
    permitida = user_may_mutate_establishment_gateway(db, current_user)
    return {
        "modo_recebimento": modo,
        "cliente_id": cliente_id,
        "gateway_configuracao_permitida": permitida,
    }


# --- Configs por estabelecimento ---
def _listar_configs_interno(
    estabelecimento_id: int,
    db: Session,
    scope: ClienteScope,
) -> List[PaymentProviderConfigResponse]:
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and estabelecimento_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
    rows = (
        db.query(PaymentProviderConfig)
        .filter(PaymentProviderConfig.cliente_id == estabelecimento_id)
        .order_by(PaymentProviderConfig.id)
        .all()
    )
    return [PaymentProviderConfigResponse.model_validate(r) for r in rows]


@router.get("/configs", response_model=List[PaymentProviderConfigResponse])
async def listar_configs(
    estabelecimento_id: int = Query(..., alias="estabelecimentoId", description="cliente_id do estabelecimento"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista configs por estabelecimento (query param estabelecimentoId)."""
    return _listar_configs_interno(estabelecimento_id, db, scope)


@router.get("/configs/{estabelecimento_id}", response_model=List[PaymentProviderConfigResponse])
async def listar_configs_por_path(
    estabelecimento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista configs por estabelecimento (path param). Equivalente a GET /configs?estabelecimentoId=."""
    return _listar_configs_interno(estabelecimento_id, db, scope)


@router.post("/configs", response_model=PaymentProviderConfigResponse, status_code=status.HTTP_201_CREATED)
async def criar_config(
    body: PaymentProviderConfigCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    if not user_may_mutate_establishment_gateway(db, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=HTTP_DETAIL_GATEWAY_SELF_SERVICE_DENIED,
        )
    provider_code = (body.provider_code or "").strip().lower()
    if provider_code not in ALLOWED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Gateway '{provider_code}' não permitido. Use: {', '.join(sorted(ALLOWED_PROVIDERS))}.",
        )
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and body.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
    # Credenciais: se body.credentials (plain) for enviado, criptografar; senão usar credentials_encrypted
    cred_enc = None
    if body.credentials is not None:
        cred_enc = encrypt_credentials(body.credentials if isinstance(body.credentials, dict) else {})
    elif getattr(body, "credentials_encrypted", None):
        cred_enc = body.credentials_encrypted
    fee = json.dumps(body.fee_configs) if body.fee_configs is not None else None
    routing = json.dumps(body.routing_rules) if body.routing_rules is not None else None
    c = PaymentProviderConfig(
        cliente_id=body.cliente_id,
        provider_code=provider_code,
        credentials_encrypted=cred_enc,
        fee_configs=fee,
        routing_rules=routing,
        is_active=body.is_active,
        is_default=body.is_default,
        test_mode=body.test_mode,
    )
    db.add(c)
    db.flush()
    if body.is_default:
        _clear_other_defaults(db, body.cliente_id, c.id)
    db.commit()
    db.refresh(c)
    return PaymentProviderConfigResponse.model_validate(c)


def _clear_other_defaults(db: Session, cliente_id: int, except_id: int) -> None:
    db.query(PaymentProviderConfig).filter(
        PaymentProviderConfig.cliente_id == cliente_id,
        PaymentProviderConfig.id != except_id,
        PaymentProviderConfig.is_default.is_(True),
    ).update({PaymentProviderConfig.is_default: False})


@router.patch("/configs/item/{config_id}", response_model=PaymentProviderConfigResponse)
async def atualizar_config_item(
    config_id: int,
    body: PaymentProviderConfigUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Atualiza flags e credenciais (MP / Pagar.me) de uma config existente. PagBank: use reconectar OAuth."""
    if not user_may_mutate_establishment_gateway(db, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=HTTP_DETAIL_GATEWAY_SELF_SERVICE_DENIED,
        )
    row = db.query(PaymentProviderConfig).filter(PaymentProviderConfig.id == config_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    if (
        body.is_active is None
        and body.is_default is None
        and body.test_mode is None
        and body.credentials is None
    ):
        raise HTTPException(status_code=400, detail="Informe ao menos um campo para atualizar.")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and row.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
    prov = (row.provider_code or "").strip().lower()
    if body.credentials is not None:
        if prov == "pagbank":
            raise HTTPException(
                status_code=400,
                detail="Para PagBank use 'Conectar conta PagBank' (OAuth). Não é possível alterar credenciais por PATCH.",
            )
        if prov not in {"mercadopago", "pagarme"}:
            raise HTTPException(status_code=400, detail="Credenciais via PATCH só para Mercado Pago ou Pagar.me.")
        creds = body.credentials if isinstance(body.credentials, dict) else {}
        row.credentials_encrypted = encrypt_credentials(creds)
    if body.is_active is not None:
        row.is_active = body.is_active
    if body.test_mode is not None:
        row.test_mode = body.test_mode
    if body.is_default is not None:
        row.is_default = body.is_default
        if body.is_default:
            _clear_other_defaults(db, row.cliente_id, row.id)
    db.commit()
    db.refresh(row)
    return PaymentProviderConfigResponse.model_validate(row)


# --- Process (via PaymentOrchestrator: provedor, split, persistência) ---
@router.post("/process", response_model=PaymentProcessResponse)
async def processar_pagamento(
    body: PaymentProcessRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and body.estabelecimento_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
    method_details = body.method_details or {}
    method = _normalize_method(body.method)
    if method not in {"credit", "debit", "pix", "boleto", "cash", "transfer"}:
        raise HTTPException(status_code=400, detail="Método de pagamento inválido")
    orchestrator = PaymentOrchestrator(db)
    try:
        result = orchestrator.process(
            cliente_id=body.estabelecimento_id,
            venda_id=body.venda_id,
            caixa_id=body.caixa_id,
            amount=body.amount,
            method=method,
            payment_submethod=method_details.get("payment_submethod"),
            installments=method_details.get("installments", 1),
            idempotency_key=body.idempotency_key,
            method_details=method_details,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return PaymentProcessResponse(
        transaction_uuid=result["transaction_uuid"],
        status=result["status"],
        provider_transaction_id=result.get("provider_transaction_id"),
        payment_details=result.get("payment_details"),
        message=result.get("message"),
        retry_allowed=result.get("retry_allowed"),
    )


@router.post("/reconcile/{transaction_uuid}")
async def reconciliar_transacao(
    transaction_uuid: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Reconcilia transacao marketplace: busca status real no Mercado Pago e atualiza."""
    tx = db.query(PaymentTransaction).filter(PaymentTransaction.uuid == transaction_uuid).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and tx.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Transação fora do escopo")
    if (tx.status or "").lower() in {"paid", "authorized", "refunded"}:
        return {
            "status": tx.status,
            "message": "Transação já finalizada",
            "transaction_uuid": tx.uuid,
        }
    if (tx.provider_code or "").lower() != "mercadopago":
        raise HTTPException(status_code=400, detail="Reconciliação disponível apenas para Mercado Pago")

    from ...core.logging import log_error
    from ...integrations.mercadopago import MercadoPagoClient
    from ...services.payments.checkout_marketplace_service import _resolve_provider_and_credentials

    try:
        _, _, credentials, _ = _resolve_provider_and_credentials(db, tx.cliente_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    access_token = credentials.get("access_token") or credentials.get("ACCESS_TOKEN") or credentials.get("token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Token de acesso não encontrado para este estabelecimento")

    client = MercadoPagoClient(access_token)
    mp_payment = None

    if tx.provider_transaction_id:
        try:
            mp_payment = await client.fetch_payment(int(tx.provider_transaction_id))
        except Exception as exc:
            log_error("reconcile fetch_payment id=%s: %s" % (tx.provider_transaction_id, exc), exc_info=exc)

    if not mp_payment and tx.pedido_id:
        try:
            mp_payment = await client.search_payments(str(tx.pedido_id))
        except Exception as exc:
            log_error("reconcile search_payments ref=%s: %s" % (tx.pedido_id, exc), exc_info=exc)

    if not mp_payment:
        return {
            "status": tx.status,
            "message": "Pagamento não encontrado no Mercado Pago",
            "transaction_uuid": tx.uuid,
        }

    mp_status = (mp_payment.get("status") or "").lower()

    if tx.pedido_id:
        from ...services.payments.webhook_marketplace_service import process_payment_notification
        process_payment_notification(db, tx, mp_status, mp_payment)
    else:
        from ...services.payments.status_map import can_transition, to_internal
        new_status = to_internal(tx.provider_code or "mercadopago", mp_status)
        if can_transition((tx.status or "pending").lower(), new_status):
            tx.status = new_status
            tx.provider_status = mp_status
            pid = mp_payment.get("id")
            if pid is not None:
                tx.provider_transaction_id = str(pid)
            if new_status in {"paid", "authorized"}:
                tx.paid_at = datetime.utcnow()
                tx.reconciliation_status = "matched"

    db.commit()
    db.refresh(tx)
    return {
        "status": tx.status,
        "provider_status": mp_status,
        "provider_transaction_id": tx.provider_transaction_id,
        "transaction_uuid": tx.uuid,
        "message": "Reconciliação concluída",
    }


@router.post("/retry/{transaction_uuid}", response_model=PaymentProcessResponse)
async def retentar_pagamento(
    transaction_uuid: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Retenta pagamento com base em transação anterior pendente/falha."""
    tx = db.query(PaymentTransaction).filter(PaymentTransaction.uuid == transaction_uuid).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and tx.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Transação fora do escopo")
    if (tx.status or "").lower() not in {"pending", "failed"}:
        raise HTTPException(status_code=400, detail="Retentativa permitida apenas para status pendente/falha")
    payer_email_retry = ""
    if tx.provider_response:
        try:
            prev = json.loads(tx.provider_response)
            payer_email_retry = (prev.get("payer_email") or "").strip()
        except Exception:
            payer_email_retry = ""
    retry_method_details = {"payer_email": payer_email_retry} if payer_email_retry else None
    orchestrator = PaymentOrchestrator(db)
    try:
        result = orchestrator.process(
            cliente_id=tx.cliente_id,
            venda_id=tx.venda_id,
            caixa_id=tx.caixa_id,
            amount=tx.amount,
            method=_normalize_method(tx.payment_method),
            payment_submethod=tx.payment_submethod,
            installments=tx.installments or 1,
            idempotency_key=f"retry:{tx.uuid}:{uuid.uuid4()}",
            method_details=retry_method_details,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return PaymentProcessResponse(
        transaction_uuid=result["transaction_uuid"],
        status=result["status"],
        provider_transaction_id=result.get("provider_transaction_id"),
        payment_details=result.get("payment_details"),
        message=result.get("message"),
        retry_allowed=result.get("retry_allowed"),
    )


# --- Comprovante HTML (para fetch com auth) ---
@router.get("/transactions/{transaction_uuid}/comprovante", response_class=HTMLResponse)
async def comprovante_html(
    transaction_uuid: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Retorna HTML do comprovante para transação paga. Usado pelo frontend com fetch (evita problema de cookie em navegação)."""
    tx = (
        db.query(PaymentTransaction)
        .options(joinedload(PaymentTransaction.pedido))
        .filter(PaymentTransaction.uuid == transaction_uuid)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and tx.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Transação fora do escopo")
    from datetime import datetime, timezone
    from pathlib import Path

    from jinja2 import Environment, FileSystemLoader

    status_lower = (tx.status or "").lower()
    status_labels = {"paid": "Pago", "authorized": "Autorizado", "pending": "Pendente", "failed": "Falhou"}
    status_label = status_labels.get(status_lower, status_lower)
    status_class = "paid" if status_lower in ("paid", "authorized") else "authorized"
    valor = f"{float(tx.amount or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    paid_at_str = tx.paid_at.strftime("%d/%m/%Y %H:%M") if tx.paid_at and hasattr(tx.paid_at, "strftime") else ""
    method_labels = {"pix": "PIX", "credit": "Cartão de crédito", "debit": "Cartão de débito", "boleto": "Boleto"}
    payment_method_label = method_labels.get((tx.payment_method or "").lower(), tx.payment_method or "-")
    tpl_dir = Path(__file__).resolve().parents[2] / "templates"
    env = Environment(loader=FileSystemLoader(str(tpl_dir)))
    tpl = env.get_template("meu_negocio/pagamentos/comprovante.html")
    html = tpl.render(
        uuid=tx.uuid,
        numero_pedido=tx.pedido.numero_pedido if tx.pedido else None,
        comprador_nome=tx.pedido.comprador_nome if tx.pedido else None,
        valor=valor,
        payment_method=payment_method_label,
        status_label=status_label,
        status_class=status_class,
        paid_at=paid_at_str,
        provider_transaction_id=tx.provider_transaction_id,
        data_geracao=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M"),
    )
    return HTMLResponse(content=html)

# --- Status por transaction uuid ---
@router.get("/status/{transaction_uuid}", response_model=PaymentStatusResponse)
async def obter_status(
    transaction_uuid: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    t = db.query(PaymentTransaction).filter(PaymentTransaction.uuid == transaction_uuid).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and t.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Transação fora do escopo")
    return PaymentStatusResponse.model_validate(t)


@router.get("/transactions", response_model=List[PaymentTransactionListItem])
async def listar_transacoes(
    estabelecimento_id: int = Query(..., alias="estabelecimentoId", description="cliente_id do estabelecimento"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filtrar por status (pending, failed, paid, authorized, etc.)",
    ),
    data_inicio: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and estabelecimento_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
    query = db.query(PaymentTransaction).filter(PaymentTransaction.cliente_id == estabelecimento_id)
    if status_filter:
        raw_statuses = [s.strip().lower() for s in status_filter.split(",") if s and s.strip()]
        if not raw_statuses:
            raise HTTPException(status_code=400, detail="status inválido")
        if len(raw_statuses) == 1:
            query = query.filter(PaymentTransaction.status == raw_statuses[0])
        else:
            query = query.filter(PaymentTransaction.status.in_(raw_statuses))
    if data_inicio:
        try:
            dt_ini = datetime.fromisoformat(data_inicio).replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(PaymentTransaction.created_at >= dt_ini)
        except ValueError:
            raise HTTPException(status_code=400, detail="data_inicio inválida. Use YYYY-MM-DD")
    if data_fim:
        try:
            dt_fim = datetime.fromisoformat(data_fim).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            query = query.filter(PaymentTransaction.created_at < dt_fim)
        except ValueError:
            raise HTTPException(status_code=400, detail="data_fim inválida. Use YYYY-MM-DD")
    rows = (
        query.options(joinedload(PaymentTransaction.pedido))
        .order_by(PaymentTransaction.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    items = []
    for r in rows:
        item = PaymentTransactionListItem.model_validate(r)
        if r.pedido_id and r.pedido:
            item.numero_pedido = r.pedido.numero_pedido
        items.append(item)
    return items


# --- Webhook por provedor ---
@router.post("/webhook/{provider_code}")
async def webhook_provedor(
    provider_code: str,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(check_webhook_rate_limit),
):
    """Recebe callbacks dos provedores (PagBank, Pagar.me, Mercado Pago). Marketplace: pedido, sessão mcs: ou order_id."""
    import json as _json

    from ...services.payments.webhook_provider_sync import apply_provider_webhook

    code = (provider_code or "").strip().lower()
    if code not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Provedor '{code}' não suportado para webhook.")

    body_bytes = await request.body()
    try:
        payload = _json.loads(body_bytes) if body_bytes else {}
    except _json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Payload inválido (não é JSON).")

    return apply_provider_webhook(db, code, payload)
