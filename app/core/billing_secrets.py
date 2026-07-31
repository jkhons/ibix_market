# PDV Ibix — Segredos de billing em repouso (Fase 4 LGPD)
"""Valores sensíveis em configuracoes: prefixo enc:v1: + Fernet (PAYMENT_CREDENTIALS_*)."""
from __future__ import annotations

from app.core.billing_config import (
    CHAVE_MP_ACCESS_TOKEN,
    CHAVE_MP_WEBHOOK_SECRET,
    CHAVE_PLATAFORMA_PAGARME_SECRET_KEY,
    CHAVE_PLATAFORMA_PAGBANK_ACCESS_TOKEN,
)
from app.services.payments.credentials import decrypt_text, encrypt_text

SECRET_PREFIX = "enc:v1:"

BILLING_SECRET_KEYS = frozenset(
    {
        CHAVE_MP_ACCESS_TOKEN,
        CHAVE_MP_WEBHOOK_SECRET,
        CHAVE_PLATAFORMA_PAGBANK_ACCESS_TOKEN,
        CHAVE_PLATAFORMA_PAGARME_SECRET_KEY,
        "payment_pagbank_connect_client_secret",
    }
)


def is_billing_secret_key(chave: str) -> bool:
    return (chave or "").strip() in BILLING_SECRET_KEYS


def encrypt_stored_secret(plain: str) -> str:
    value = (plain or "").strip()
    if not value:
        return ""
    encrypted = encrypt_text(value)
    if encrypted is None:
        raise RuntimeError(
            "Criptografia indisponível: defina PAYMENT_CREDENTIALS_SECRET ou PAYMENT_CREDENTIALS_PASSWORD."
        )
    if encrypted == value:
        return value
    return f"{SECRET_PREFIX}{encrypted}"


def decrypt_stored_secret(stored: str) -> str:
    raw = (stored or "").strip()
    if not raw:
        return ""
    if raw.startswith(SECRET_PREFIX):
        decrypted = decrypt_text(raw[len(SECRET_PREFIX) :])
        return (decrypted or "").strip()
    return raw
