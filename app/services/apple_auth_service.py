# PDV Ibix - Apple Sign-In server-side verification (JWKS)
"""Valida o id_token retornado pelo Sign In with Apple usando JWKS público da Apple."""
import logging
import time
from typing import Any, Dict, Optional

import httpx
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

_jwks_cache: Optional[Dict[str, Any]] = None
_jwks_cache_ts: float = 0
JWKS_CACHE_TTL = 3600


async def _get_apple_jwks() -> Dict[str, Any]:
    global _jwks_cache, _jwks_cache_ts
    now = time.time()
    if _jwks_cache and (now - _jwks_cache_ts) < JWKS_CACHE_TTL:
        return _jwks_cache
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(APPLE_JWKS_URL)
        resp.raise_for_status()
    _jwks_cache = resp.json()
    _jwks_cache_ts = now
    return _jwks_cache


async def verify_apple_id_token(id_token: str, client_id: str) -> Dict[str, Any]:
    """
    Valida o id_token da Apple e retorna o payload decodificado.
    Campos úteis: sub (Apple user ID), email, email_verified.
    Lança JWTError ou ValueError se inválido.
    """
    jwks = await _get_apple_jwks()
    try:
        header = jwt.get_unverified_header(id_token)
    except JWTError as e:
        raise ValueError(f"id_token header inválido: {e}")

    kid = header.get("kid")
    if not kid:
        raise ValueError("id_token sem kid no header")

    key = None
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            key = k
            break
    if not key:
        _jwks_cache_ts = 0
        jwks = await _get_apple_jwks()
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                key = k
                break
    if not key:
        raise ValueError(f"JWK com kid={kid} não encontrada na Apple")

    payload = jwt.decode(
        id_token,
        key,
        algorithms=["RS256"],
        audience=client_id,
        issuer=APPLE_ISSUER,
    )
    return payload
