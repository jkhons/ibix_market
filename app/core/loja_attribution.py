# PDV Ibix — Atribuição vitrine (compartilhamento social → pedido)
"""Cookie first-party + UTMs só em links de partilha (Fase 02)."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import Request
from starlette.responses import Response

# Presença do cookie indica que o utilizador entrou na vitrine via link de partilha (UTM).
VITRINE_SHARE_COOKIE_NAME = "ibix_vitrine_share"
VITRINE_SHARE_COOKIE_VALUE = "1"

_UTM_PARAM_KEYS = frozenset(
    k.lower()
    for k in ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")
)


def strip_utm_params_from_path_query(request: Request) -> str:
    """Path + query sem parâmetros UTM (mantém outros query params)."""
    path = request.url.path
    items = [(k, v) for k, v in request.query_params.multi_items() if k.lower() not in _UTM_PARAM_KEYS]
    if not items:
        return path
    return path + "?" + urlencode(items)


def set_vitrine_share_attribution_cookie(response: Response, request: Request, max_age_days: int = 14) -> None:
    """Define cookie HttpOnly; leitura no POST /checkout (servidor)."""
    secure = request.url.scheme == "https"
    response.set_cookie(
        key=VITRINE_SHARE_COOKIE_NAME,
        value=VITRINE_SHARE_COOKIE_VALUE,
        max_age=max_age_days * 86400,
        path="/",
        httponly=True,
        samesite="lax",
        secure=secure,
    )


def vitrine_share_cookie_present(request: Request) -> bool:
    return request.cookies.get(VITRINE_SHARE_COOKIE_NAME) == VITRINE_SHARE_COOKIE_VALUE
