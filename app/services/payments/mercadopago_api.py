# PDV Ibix — URLs e parsing de erros/respostas comuns à API Mercado Pago (Payments + Preferences).
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import httpx

from app.utils.mercadopago_errors import (
    looks_like_mp_html_payload,
    mp_api_failure_message,
    sanitize_mp_json_field,
)

MP_PREFERENCES_URL = "https://api.mercadopago.com/checkout/preferences"
MP_PAYMENTS_URL = "https://api.mercadopago.com/v1/payments"
MP_USERS_ME_URL = "https://api.mercadolibre.com/users/me"


def mercadopago_response_meta(response: httpx.Response) -> str:
    bits: list[str] = []
    rid = response.headers.get("x-request-id") or response.headers.get("x-socket-timeout")
    if rid:
        bits.append(f"x-request-id={rid}")
    ct = response.headers.get("content-type")
    if ct:
        bits.append(f"content-type={ct[:80]}")
    return ("; " + ", ".join(bits)) if bits else ""


def format_mercadopago_api_error(response: httpx.Response) -> str:
    code = response.status_code
    reason = (getattr(response, "reason_phrase", None) or "").strip()
    base = f"HTTP {code}" + (f" {reason}" if reason else "")
    raw = (response.text or "").strip()
    meta = mercadopago_response_meta(response)
    if not raw:
        hint = ""
        if code == 403:
            hint = (
                " | corpo vazio: em geral Access Token inválido/revogado, ambiente teste×produção trocados, "
                "ou credencial que não é APP_USR (use o Access Token de produção em Suas integrações)."
            )
        return base + meta + hint
    try:
        body = response.json()
    except Exception:
        return f"{base}: {mp_api_failure_message(code, raw, response.headers.get('content-type'))}" + meta
    if not isinstance(body, dict):
        return f"{base}: {mp_api_failure_message(code, raw, response.headers.get('content-type'))}" + meta
    parts: list[str] = []
    m = sanitize_mp_json_field(body.get("message"))
    if m:
        parts.append(str(m))
    err_raw = body.get("error")
    err = sanitize_mp_json_field(err_raw) if err_raw is not None else None
    if err and str(err) != str(m or ""):
        parts.append(str(err))
    cause = body.get("cause")
    if isinstance(cause, list):
        for item in cause[:8]:
            if isinstance(item, dict):
                cd = item.get("code") or item.get("type") or ""
                desc = item.get("description") or item.get("message") or ""
                if desc or cd:
                    desc_s = sanitize_mp_json_field(desc) or (
                        desc[:120] if isinstance(desc, str) and not looks_like_mp_html_payload(desc) else ""
                    )
                    if not desc_s and isinstance(desc, str) and looks_like_mp_html_payload(desc):
                        desc_s = "(descrição omitida: HTML)"
                    seg = f"{cd}: {desc_s}".strip(": ").strip() if cd else desc_s
                    if seg:
                        parts.append(seg)
            elif item:
                s_it = str(item).strip()
                if looks_like_mp_html_payload(s_it):
                    parts.append("(item omitido: resposta HTML)")
                else:
                    parts.append(s_it[:200])
    elif cause:
        s_c = str(cause).strip()
        parts.append("(cause omitida: HTML)" if looks_like_mp_html_payload(s_c) else s_c[:300])
    if parts:
        return f"{base}: " + " | ".join(parts)[:900] + meta
    if looks_like_mp_html_payload(raw):
        return f"{base}: {mp_api_failure_message(code, raw, response.headers.get('content-type'))}" + meta
    return f"{base}: {raw[:500]}" + meta


def mp_payer_identification_from_document(raw: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Monta payer.identification para Preferências Checkout Pro (BR).
    Sem CPF/CNPJ válido na preferência, o MP costuma manter o fluxo de cartão incompleto (botão Pagar desabilitado).
    """
    if not raw:
        return None
    digits = "".join(c for c in str(raw) if c.isdigit())
    if len(digits) == 11:
        return {"type": "CPF", "number": digits}
    if len(digits) == 14:
        return {"type": "CNPJ", "number": digits}
    return None


def validate_mercadopago_access_token(access_token: str) -> Optional[str]:
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(MP_USERS_ME_URL, headers={"Authorization": f"Bearer {access_token}"})
        if r.is_success:
            return None
        return format_mercadopago_api_error(r)
    except Exception as ex:
        return f"erro ao validar token: {ex}"[:300]


def extract_pix_from_mp_payment_body(body: Dict[str, Any]) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[int], str]:
    """
    Retorna: qr_code, qr_code_base64, ticket_url, date_of_expiration_iso, payment_id, status
    """
    pid = body.get("id")
    status = str(body.get("status") or "pending")
    poi = body.get("point_of_interaction") or {}
    td = poi.get("transaction_data") or {}
    qr = (td.get("qr_code") or "").strip() or ""
    qr_b64 = td.get("qr_code_base64")
    if isinstance(qr_b64, str):
        qr_b64 = qr_b64.strip() or None
    else:
        qr_b64 = None
    ticket_url = td.get("ticket_url")
    if isinstance(ticket_url, str):
        ticket_url = ticket_url.strip() or None
    else:
        ticket_url = None
    exp_iso = body.get("date_of_expiration")
    if isinstance(exp_iso, str):
        exp_iso = exp_iso.strip() or None
    else:
        exp_iso = None
    return qr, qr_b64, ticket_url, exp_iso, pid, status


def minutes_until_mp_expiration(date_of_expiration_iso: Optional[str], default_minutes: int = 30) -> int:
    if not date_of_expiration_iso:
        return default_minutes
    try:
        raw = date_of_expiration_iso.replace("Z", "+00:00")
        exp = datetime.fromisoformat(raw)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (exp - now).total_seconds() / 60.0
        return max(1, min(int(round(delta)), 30 * 24 * 60))
    except Exception:
        return default_minutes
