# PDV Ibix — Evita exibir HTML de páginas de erro do MP (mlstatic, WAF) no admin / logs legíveis.
from __future__ import annotations

from typing import Optional


def looks_like_mp_html_payload(text: Optional[str]) -> bool:
    """True se o corpo parece página HTML (erro CDN/WAF) em vez de JSON da API."""
    if not text:
        return False
    s = text.lstrip()[:12000]
    low = s.lower()
    if low.startswith("<!doctype") or low.startswith("<html"):
        return True
    if "<head" in low[:4000] and ("<meta" in low[:6000] or "<link" in low[:6000]):
        return True
    if "mlstatic.com" in low or "http2.mlstatic.com" in low:
        return True
    if s.count("<") > 10 and "<body" in low[:8000]:
        return True
    return False


def mp_api_failure_message(
    http_status: int,
    raw_text: Optional[str],
    content_type: Optional[str] = None,
) -> str:
    """
    Texto seguro para UI e logs quando a API MP não retorna JSON (ex.: 403 com HTML).
    """
    ct = (content_type or "").lower()
    raw = raw_text or ""
    if "text/html" in ct or looks_like_mp_html_payload(raw):
        return (
            f"O Mercado Pago respondeu com página HTML (HTTP {http_status}), não JSON — "
            "em geral Access Token inválido/revogado, credencial de teste em produção ou bloqueio de rede. "
            "Use um Access Token de produção (APP_USR-…) em Suas integrações e salve em Admin Billing."
        )
    t = raw.strip()
    if not t:
        return f"HTTP {http_status} (resposta sem corpo útil)."
    if looks_like_mp_html_payload(t):
        return mp_api_failure_message(http_status, None, "text/html")
    return t[:500]


def sanitize_mp_json_field(value: Optional[str]) -> Optional[str]:
    """Evita message/error JSON que venham com HTML acidental."""
    if value is None:
        return None
    s = str(value).strip()
    if looks_like_mp_html_payload(s):
        return None
    return s[:500] if s else None
