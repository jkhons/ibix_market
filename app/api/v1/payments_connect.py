# PDV Ibix - OAuth Connect para gateways de pagamento
"""Fluxo OAuth para PagBank Connect: start (redirect) + callback (troca code por token)."""
import hashlib
import hmac
import os
import secrets
import time
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from ...core.pagbank_config import (
    get_pagbank_client_id,
    get_pagbank_connect_url,
)
from ...core.payment_gateway_policy import (
    HTTP_DETAIL_GATEWAY_SELF_SERVICE_DENIED,
    user_may_mutate_establishment_gateway,
)
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models import PaymentProviderConfig, Usuario
from ...services.payments.credentials import encrypt_credentials
from ...services.payments.pagbank_token_service import exchange_code_for_token

router = APIRouter(prefix="/payments/connect", tags=["Pagamentos - OAuth Connect"])

_STATE_TTL_SECONDS = 900  # 15 minutos

PAGBANK_SCOPES = "payments.create+payments.read+payments.refund+accounts.read"


def _get_app_url() -> str:
    """Retorna APP_URL configurada no ambiente."""
    url = os.environ.get("APP_URL", "").strip().rstrip("/")
    if not url:
        raise ValueError("APP_URL não configurada no ambiente. Necessária para OAuth redirect_uri.")
    return url


def _generate_state(cliente_id: int, user_id: int) -> str:
    """Gera state assinado para OAuth (HMAC-SHA256 com SECRET_KEY)."""
    secret = os.environ.get("SECRET_KEY", "")
    if not secret:
        raise ValueError("SECRET_KEY não configurada. Necessária para segurança do fluxo OAuth.")
    nonce = secrets.token_hex(16)
    ts = str(int(time.time()))
    payload = f"{cliente_id}:{user_id}:{ts}:{nonce}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def _validate_state(state: str) -> tuple:
    """Valida state OAuth. Retorna (cliente_id, user_id) ou lança exceção."""
    secret = os.environ.get("SECRET_KEY", "")
    if not secret:
        raise HTTPException(status_code=500, detail="SECRET_KEY não configurada.")
    parts = state.split(":")
    if len(parts) != 5:
        raise HTTPException(status_code=400, detail="State OAuth inválido.")
    cliente_id_str, user_id_str, ts_str, nonce, sig_received = parts
    payload = f"{cliente_id_str}:{user_id_str}:{ts_str}:{nonce}"
    sig_expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig_received, sig_expected):
        raise HTTPException(status_code=400, detail="Assinatura do state OAuth inválida.")
    try:
        ts = int(ts_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Timestamp do state inválido.")
    if time.time() - ts > _STATE_TTL_SECONDS:
        raise HTTPException(status_code=400, detail="State OAuth expirado. Tente conectar novamente.")
    return int(cliente_id_str), int(user_id_str)


def _get_redirect_uri() -> str:
    app_url = _get_app_url()
    return f"{app_url}/api/v1/payments/connect/pagbank/callback"


# --- PagBank OAuth ---

@router.get("/pagbank/start")
async def pagbank_oauth_start(
    request: Request,
    estabelecimento_id: int = Query(..., alias="estabelecimentoId", description="cliente_id do estabelecimento"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Inicia fluxo OAuth PagBank Connect: redireciona o CA para a página de autorização do PagBank."""
    if scope.must_filter_by_cliente():
        allowed = scope.allowed_ids or []
        if estabelecimento_id not in allowed:
            raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo do usuário.")

    if not user_may_mutate_establishment_gateway(db, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=HTTP_DETAIL_GATEWAY_SELF_SERVICE_DENIED,
        )

    client_id = get_pagbank_client_id(db)
    connect_url = get_pagbank_connect_url(db)
    redirect_uri = _get_redirect_uri()
    state = _generate_state(estabelecimento_id, current_user.id)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": PAGBANK_SCOPES,
        "state": state,
    }
    authorize_url = f"{connect_url}/oauth2/authorize?{urlencode(params)}"
    return RedirectResponse(url=authorize_url, status_code=302)


@router.get("/pagbank/callback")
async def pagbank_oauth_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Callback OAuth PagBank: recebe code, troca por access_token e salva config do estabelecimento."""
    recebiveis_url = "/negocio/recebiveis"

    if error:
        return RedirectResponse(
            url=f"{recebiveis_url}?connect=pagbank_error&msg=Autorizacao+negada+pelo+vendedor",
            status_code=302,
        )

    if not code or not state:
        return RedirectResponse(
            url=f"{recebiveis_url}?connect=pagbank_error&msg=Parametros+ausentes+no+callback",
            status_code=302,
        )

    try:
        cliente_id, user_id = _validate_state(state)
    except HTTPException as e:
        return RedirectResponse(
            url=f"{recebiveis_url}?connect=pagbank_error&msg={e.detail.replace(' ', '+')}",
            status_code=302,
        )

    redirect_uri = _get_redirect_uri()

    try:
        token_data = exchange_code_for_token(db, code, redirect_uri)
    except Exception as exc:
        msg = str(exc)[:200].replace(" ", "+")
        return RedirectResponse(
            url=f"{recebiveis_url}?connect=pagbank_error&msg={msg}",
            status_code=302,
        )

    creds_to_store = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token"),
        "expires_in": token_data.get("expires_in"),
        "account_id": token_data.get("account_id"),
    }

    existing = (
        db.query(PaymentProviderConfig)
        .filter(
            PaymentProviderConfig.cliente_id == cliente_id,
            PaymentProviderConfig.provider_code == "pagbank",
        )
        .first()
    )

    if existing:
        existing.credentials_encrypted = encrypt_credentials(creds_to_store)
        existing.account_external_id = token_data.get("account_id")
        existing.connection_status = "connected"
        existing.is_active = True
        existing.last_error = None
    else:
        config = PaymentProviderConfig(
            cliente_id=cliente_id,
            provider_code="pagbank",
            credentials_encrypted=encrypt_credentials(creds_to_store),
            account_external_id=token_data.get("account_id"),
            connection_status="connected",
            is_active=True,
            is_default=False,
            test_mode=False,
        )
        db.add(config)

    db.commit()

    return RedirectResponse(
        url=f"{recebiveis_url}?connect=pagbank_success",
        status_code=302,
    )
