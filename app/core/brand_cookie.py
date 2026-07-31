# PDV Ibix — Cookies escopados por host (multi-brand Fase 3.1)
"""Nunca definir Domain compartilhado entre marcas; cookie isolado pelo host do navegador."""
from __future__ import annotations

import os
from typing import Optional

from fastapi import Request
from starlette.responses import Response


def request_is_https(request: Optional[Request]) -> bool:
    if request is None:
        return os.getenv("HTTPS", "").lower() in ("true", "1")
    if os.getenv("HTTPS", "").lower() in ("true", "1"):
        return True
    if request.url.scheme == "https":
        return True
    forwarded = (request.headers.get("x-forwarded-proto") or "").strip().lower()
    return forwarded == "https"


def apply_host_scoped_cookie(
    response: Response,
    *,
    key: str,
    value: str,
    request: Optional[Request] = None,
    max_age: int = 28800,
    httponly: bool = False,
    path: str = "/",
) -> None:
    """Define cookie sem atributo Domain (host-only)."""
    response.set_cookie(
        key=key,
        value=value,
        httponly=httponly,
        secure=request_is_https(request),
        samesite="lax",
        max_age=max_age,
        path=path,
    )


def clear_pdv_auth_cookies(response: Response, request: Optional[Request] = None) -> None:
    """Remove cookies PDV (mesmos atributos path/secure/samesite do login)."""
    secure = request_is_https(request)
    for key in ("pdv_solumatica_token", "pdv_automscale_token"):
        response.delete_cookie(key=key, path="/", secure=secure, samesite="lax")
