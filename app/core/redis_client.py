# PDV Ibix - Cliente Redis compartilhado (cache, rate limit, blacklist)
# Conexão com pool, timeout, prefixo de chaves e fallback em caso de indisponibilidade.
# Boas práticas: prefixo evita colisão com Celery/outros; pool limita conexões; timeout evita travamento.
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import redis

_redis_client: Optional[redis.Redis] = None
_redis_available: bool = True

# Prefixo global para todas as chaves (cache, rate limit, blacklist). Evita colisão se Redis for compartilhado.
REDIS_KEY_PREFIX = (os.getenv("REDIS_KEY_PREFIX") or "pdv:").strip() or "pdv:"


def get_redis_key_prefix() -> str:
    """Retorna o prefixo de chaves (para scripts e testes que precisam construir chaves)."""
    return REDIS_KEY_PREFIX


def prefix_key(key: str) -> str:
    """Retorna a chave com o prefixo do app. Use em todas as operações Redis (cache, rate limit, blacklist)."""
    if key.startswith(REDIS_KEY_PREFIX):
        return key
    return f"{REDIS_KEY_PREFIX}{key}"


def get_redis_client() -> Optional[redis.Redis]:
    """Retorna cliente Redis com pool. None se indisponível (fallback)."""
    global _redis_client, _redis_available
    if not _redis_available and _redis_client is None:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        timeout = int(os.getenv("REDIS_TIMEOUT", "2"))
        max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
        _redis_client = redis.from_url(
            url,
            socket_timeout=timeout,
            socket_connect_timeout=timeout,
            decode_responses=True,
            max_connections=max_connections,
        )
        _redis_client.ping()
        return _redis_client
    except Exception:
        _redis_available = False
        _redis_client = None
        return None


def redis_available() -> bool:
    """Verifica se Redis está disponível."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.ping()
        return True
    except Exception:
        return False


def invalidate_redis_client() -> None:
    """Invalida cliente (útil para testes ou reconexão)."""
    global _redis_client, _redis_available
    if _redis_client:
        try:
            _redis_client.close()
        except Exception:
            pass
    _redis_client = None
    _redis_available = True
