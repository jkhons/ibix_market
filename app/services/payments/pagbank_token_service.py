# PDV Ibix - Serviço de refresh de token PagBank Connect
"""Troca code por access_token e renova tokens expirados."""
from typing import Any, Dict

import httpx
from sqlalchemy.orm import Session

from app.core.pagbank_config import (
    get_pagbank_base_url,
    get_pagbank_client_id,
    get_pagbank_client_secret,
)
from app.models import PaymentProviderConfig
from app.services.payments.credentials import decrypt_credentials, encrypt_credentials


def exchange_code_for_token(
    db: Session,
    code: str,
    redirect_uri: str,
) -> Dict[str, Any]:
    """
    Troca authorization code por access_token no PagBank.
    Retorna dict com access_token, refresh_token, expires_in, account_id, scope.
    Lança exceção em caso de erro.
    """
    client_id = get_pagbank_client_id(db)
    client_secret = get_pagbank_client_secret(db)
    base_url = get_pagbank_base_url(db)

    url = f"{base_url}/oauth2/token"
    headers = {
        "Authorization": f"Bearer {client_id}",
        "Content-Type": "application/json",
        "X_CLIENT_ID": client_id,
        "X_CLIENT_SECRET": client_secret,
    }
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=body, headers=headers)

    if not response.is_success:
        try:
            err = response.json()
            msg = err.get("error_messages", [{}])
            if isinstance(msg, list) and msg:
                msg = msg[0].get("description", "") or str(err)
            else:
                msg = str(err)
        except Exception:
            msg = response.text[:500]
        raise RuntimeError(f"Erro ao trocar code PagBank: {msg} (HTTP {response.status_code})")

    data = response.json()
    required_fields = ("access_token",)
    for field in required_fields:
        if not data.get(field):
            raise RuntimeError(f"Resposta PagBank incompleta: campo '{field}' ausente.")

    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "expires_in": data.get("expires_in"),
        "account_id": data.get("account_id"),
        "scope": data.get("scope"),
        "token_type": data.get("token_type", "bearer"),
    }


def refresh_pagbank_token(
    db: Session,
    config: PaymentProviderConfig,
) -> Dict[str, Any]:
    """
    Renova access_token de uma config PagBank usando refresh_token.
    Atualiza credentials_encrypted na config e faz commit.
    Retorna dict com novos tokens.
    """
    creds = decrypt_credentials(config.credentials_encrypted)
    if not creds or not creds.get("refresh_token"):
        raise ValueError("Config PagBank não possui refresh_token para renovação.")

    client_id = get_pagbank_client_id(db)
    client_secret = get_pagbank_client_secret(db)
    base_url = get_pagbank_base_url(db)

    url = f"{base_url}/oauth2/refresh"
    headers = {
        "Authorization": f"Bearer {client_id}",
        "Content-Type": "application/json",
        "X_CLIENT_ID": client_id,
        "X_CLIENT_SECRET": client_secret,
    }
    body = {
        "grant_type": "refresh_token",
        "refresh_token": creds["refresh_token"],
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=body, headers=headers)

    if not response.is_success:
        try:
            err = response.json()
            msg = str(err)
        except Exception:
            msg = response.text[:500]
        config.connection_status = "token_expired"
        config.last_error = f"Falha ao renovar token: {msg}"
        db.commit()
        raise RuntimeError(f"Falha ao renovar token PagBank: {msg}")

    data = response.json()
    if not data.get("access_token"):
        raise RuntimeError("Resposta PagBank incompleta ao renovar token.")

    new_creds = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token") or creds.get("refresh_token"),
        "expires_in": data.get("expires_in"),
        "account_id": data.get("account_id") or creds.get("account_id"),
    }
    config.credentials_encrypted = encrypt_credentials(new_creds)
    config.connection_status = "connected"
    config.last_error = None
    db.commit()

    return new_creds


def get_pagbank_access_token(db: Session, config: PaymentProviderConfig) -> str:
    """
    Obtém access_token válido para uma config PagBank.
    Se expirado, tenta renovar automaticamente.
    """
    creds = decrypt_credentials(config.credentials_encrypted)
    if not creds or not creds.get("access_token"):
        raise ValueError("Config PagBank não possui access_token. Reconecte a conta em Recebíveis.")
    return creds["access_token"]
