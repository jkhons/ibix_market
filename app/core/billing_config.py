# PDV Ibix - Leitura de config billing (MP + APP_URL + valor mensal + desconto): DB (Configuracao) ou env
"""Permite configurar MP_ACCESS_TOKEN, MP_WEBHOOK_SECRET, APP_URL, valor mensal e descontos
pelo painel Admin Billing. Quando há sessão DB, prioriza tabela configuracoes (chaves billing_*)."""
from typing import List, Optional

from sqlalchemy.orm import Session

CHAVE_MP_ACCESS_TOKEN = "billing_mp_access_token"
CHAVE_MP_PUBLIC_KEY = "billing_mp_public_key"
CHAVE_MP_WEBHOOK_SECRET = "billing_mp_webhook_secret"
# Token/conta da plataforma quando Empresa.modo_recebimento=plataforma e gateway_plataforma=pagbank|pagarme
CHAVE_PLATAFORMA_PAGBANK_ACCESS_TOKEN = "billing_plataforma_pagbank_access_token"
CHAVE_PLATAFORMA_PAGARME_SECRET_KEY = "billing_plataforma_pagarme_secret_key"
CHAVE_APP_URL = "billing_app_url"
CHAVE_VALOR_MENSAL_CENTAVOS = "billing_valor_mensal_centavos"
CHAVE_VALOR_APLICAR_A = "billing_valor_aplicar_a"  # todos | novos
CHAVE_DESCONTO_PERCENT = "billing_desconto_percent"
CHAVE_DESCONTO_ESCOPO = "billing_desconto_escopo"  # todos | ca | admin_cliente | especifico
CHAVE_DESCONTO_TENANT_IDS = "billing_desconto_tenant_ids"  # quando escopo=especifico


def _get_from_db(db: Optional[Session], chave: str) -> Optional[str]:
    if not db:
        return None
    from app.models import Configuracao

    row = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    if row and row.valor is not None and str(row.valor).strip():
        raw = str(row.valor).strip()
        from app.core.billing_secrets import decrypt_stored_secret, is_billing_secret_key

        if is_billing_secret_key(chave):
            return decrypt_stored_secret(raw)
        return raw
    return None


def get_mp_access_token(db: Optional[Session] = None) -> str:
    """Access Token Mercado Pago. Ordem: Configuracao(billing_mp_access_token) → env MP_ACCESS_TOKEN."""
    import os
    val = _get_from_db(db, CHAVE_MP_ACCESS_TOKEN)
    if val is not None:
        return val
    return (os.getenv("MP_ACCESS_TOKEN") or "").strip()


def get_mp_public_key(db: Optional[Session] = None) -> str:
    """Public Key Mercado Pago (frontend/brick). Ordem: Configuracao(billing_mp_public_key) → env MP_PUBLIC_KEY."""
    import os
    val = _get_from_db(db, CHAVE_MP_PUBLIC_KEY)
    if val is not None:
        return val
    return (os.getenv("MP_PUBLIC_KEY") or "").strip()


def get_plataforma_pagbank_access_token(db: Optional[Session] = None) -> str:
    """Access token PagBank para checkout marketplace em modo plataforma (não é OAuth do CA)."""
    import os

    val = _get_from_db(db, CHAVE_PLATAFORMA_PAGBANK_ACCESS_TOKEN)
    if val is not None:
        return val
    return (os.getenv("PLATAFORMA_PAGBANK_ACCESS_TOKEN") or "").strip()


def get_plataforma_pagarme_secret_key(db: Optional[Session] = None) -> str:
    """Secret Key Pagar.me para checkout marketplace em modo plataforma."""
    import os

    val = _get_from_db(db, CHAVE_PLATAFORMA_PAGARME_SECRET_KEY)
    if val is not None:
        return val
    return (os.getenv("PLATAFORMA_PAGARME_SECRET_KEY") or "").strip()


def get_mp_webhook_secret(db: Optional[Session] = None) -> str:
    """Webhook secret MP. Ordem: Configuracao(billing_mp_webhook_secret) → env MP_WEBHOOK_SECRET."""
    import os
    val = _get_from_db(db, CHAVE_MP_WEBHOOK_SECRET)
    if val is not None:
        return val
    return (os.getenv("MP_WEBHOOK_SECRET") or "").strip()


def get_app_url(db: Optional[Session] = None) -> str:
    """URL base da aplicação. Ordem: Configuracao(billing_app_url) → env APP_URL."""
    import os
    val = _get_from_db(db, CHAVE_APP_URL)
    if val is not None:
        return val.rstrip("/")
    return (os.getenv("APP_URL") or "").strip().rstrip("/")


def get_valor_mensal_centavos(db: Optional[Session] = None) -> int:
    """Valor padrão da mensalidade em centavos. Configuracao → fallback 49000.
    Ex.: 19900 = R$ 199,00 (configurar em Admin Billing > Preço)."""
    val = _get_from_db(db, CHAVE_VALOR_MENSAL_CENTAVOS)
    if val is not None:
        try:
            return int(val)
        except ValueError:
            pass
    return 49000


def get_valor_aplicar_a(db: Optional[Session] = None) -> str:
    """Aplicar valor a: 'todos' (todos assinantes) ou 'novos' (só novos)."""
    val = _get_from_db(db, CHAVE_VALOR_APLICAR_A)
    if val in ("todos", "novos"):
        return val
    return "novos"


def get_desconto_percent(db: Optional[Session] = None) -> int:
    """Desconto em percentual (0-100)."""
    val = _get_from_db(db, CHAVE_DESCONTO_PERCENT)
    if val is not None:
        try:
            return max(0, min(100, int(val)))
        except ValueError:
            pass
    return 0


def get_desconto_escopo(db: Optional[Session] = None) -> str:
    """Escopo do desconto: todos | ca | admin_cliente | especifico."""
    val = _get_from_db(db, CHAVE_DESCONTO_ESCOPO)
    if val in ("todos", "ca", "admin_cliente", "especifico"):
        return val
    return "todos"


def get_desconto_tenant_ids(db: Optional[Session] = None) -> List[int]:
    """Lista de tenant_id com desconto quando escopo=especifico."""
    val = _get_from_db(db, CHAVE_DESCONTO_TENANT_IDS)
    if not val or not val.strip():
        return []
    out = []
    for s in val.split(","):
        s = s.strip()
        if s.isdigit():
            out.append(int(s))
    return out
