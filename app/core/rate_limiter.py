#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDV Ibix - Sistema de Rate Limiting
Proteção contra ataques e limitação de requisições.
Suporta Redis (distribuído) com fallback para memória.
"""

import asyncio
import os
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request, status

from ..core.logging import log_error
from ..core.redis_client import get_redis_client, prefix_key


class RedisRateLimiter:
    """Rate limiter distribuído via Redis. Fallback para memória se Redis indisponível."""

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        block_duration: int = 300,
        key_prefix: str = "rate:api",
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.block_duration = block_duration
        self.key_prefix = key_prefix
        self._memory_fallback = RateLimiter()
        self._memory_fallback.max_requests = max_requests
        self._memory_fallback.window_seconds = window_seconds
        self._memory_fallback.block_duration = block_duration

    def is_allowed(self, ip: str) -> Tuple[bool, Optional[str]]:
        redis_client = get_redis_client()
        if redis_client is None:
            return self._memory_fallback.is_allowed(ip)

        try:
            count_key = prefix_key(f"{self.key_prefix}:{ip}")
            block_key = prefix_key(f"block:{self.key_prefix}:{ip}")

            if redis_client.exists(block_key):
                ttl = redis_client.ttl(block_key)
                return False, f"IP bloqueado por {max(0, ttl)} segundos"

            pipe = redis_client.pipeline()
            pipe.incr(count_key)
            pipe.ttl(count_key)
            results = pipe.execute()
            current = results[0]
            ttl = results[1]

            if ttl == -1:
                redis_client.expire(count_key, self.window_seconds)

            if current > self.max_requests:
                redis_client.setex(block_key, self.block_duration, "1")
                log_error(
                    f"RATE_LIMIT_EXCEEDED - IP:{ip} - Excedeu {self.max_requests} "
                    f"requisições em {self.window_seconds}s"
                )
                return False, (
                    f"Limite de {self.max_requests} requisições por "
                    f"{self.window_seconds}s excedido"
                )
            return True, None
        except Exception:
            return self._memory_fallback.is_allowed(ip)


class RateLimiter:
    """Sistema de rate limiting para o PDV Ibix"""
    
    def __init__(self):
        # Armazenar requisições por IP
        self.requests: Dict[str, list] = defaultdict(list)
        
        # Configurações de rate limiting
        self.max_requests = 100  # Máximo de requisições por janela
        self.window_seconds = 60  # Janela de tempo em segundos
        self.block_duration = 300  # Duração do bloqueio em segundos
        
        # IPs bloqueados
        self.blocked_ips: Dict[str, float] = {}
        
        # Limpeza automática
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # Limpeza a cada 5 minutos
    
    def is_allowed(self, ip: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica se o IP pode fazer uma requisição
        
        Returns:
            Tuple[bool, Optional[str]]: (permitido, mensagem_erro)
        """
        current_time = time.time()
        
        # Verificar se o IP está bloqueado
        if ip in self.blocked_ips:
            if current_time - self.blocked_ips[ip] < self.block_duration:
                remaining = int(self.block_duration - (current_time - self.blocked_ips[ip]))
                return False, f"IP bloqueado por {remaining} segundos"
            else:
                # Remover do bloqueio
                del self.blocked_ips[ip]
        
        # Limpeza automática
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_requests(current_time)
            self.last_cleanup = current_time
        
        # Adicionar requisição atual
        self.requests[ip].append(current_time)
        
        # Filtrar requisições dentro da janela
        window_start = current_time - self.window_seconds
        recent_requests = [req for req in self.requests[ip] if req > window_start]
        self.requests[ip] = recent_requests
        
        # Verificar limite
        if len(recent_requests) > self.max_requests:
            # Bloquear IP
            self.blocked_ips[ip] = current_time
            log_error(f"RATE_LIMIT_EXCEEDED - IP:{ip} - Excedeu {self.max_requests} requisições em {self.window_seconds}s")
            return False, f"Limite de {self.max_requests} requisições por {self.window_seconds}s excedido"
        
        return True, None
    
    def _cleanup_old_requests(self, current_time: float):
        """Limpa requisições antigas"""
        window_start = current_time - self.window_seconds
        
        # Limpar requisições antigas
        for ip in list(self.requests.keys()):
            self.requests[ip] = [req for req in self.requests[ip] if req > window_start]
            if not self.requests[ip]:
                del self.requests[ip]
        
        # Limpar IPs bloqueados expirados
        for ip in list(self.blocked_ips.keys()):
            if current_time - self.blocked_ips[ip] > self.block_duration:
                del self.blocked_ips[ip]
    
    def get_stats(self, ip: str) -> Dict:
        """Retorna estatísticas de rate limiting para um IP"""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        recent_requests = [req for req in self.requests[ip] if req > window_start]
        
        return {
            "ip": ip,
            "requests_in_window": len(recent_requests),
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "is_blocked": ip in self.blocked_ips,
            "block_remaining": max(0, int(self.block_duration - (current_time - self.blocked_ips[ip]))) if ip in self.blocked_ips else 0
        }

# Rate limiters: Redis com fallback para memória
rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_MAX", "100")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
    block_duration=int(os.getenv("RATE_LIMIT_BLOCK", "300")),
    key_prefix="rate:api",
)

login_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("LOGIN_RATE_LIMIT_MAX", "10")),
    window_seconds=int(os.getenv("LOGIN_RATE_LIMIT_WINDOW", "60")),
    block_duration=int(os.getenv("LOGIN_RATE_LIMIT_BLOCK", "300")),
    key_prefix="rate:login",
)

register_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("REGISTER_RATE_LIMIT_MAX", "30")),
    window_seconds=int(os.getenv("REGISTER_RATE_LIMIT_WINDOW", "900")),
    block_duration=int(os.getenv("REGISTER_RATE_LIMIT_BLOCK", "600")),
    key_prefix="rate:register",
)

# Limite por tenant (rotas autenticadas). Quando tenant_id for None (ex.: Superadmin), não aplica este limite.
tenant_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_TENANT_MAX", "200")),
    window_seconds=int(os.getenv("RATE_LIMIT_TENANT_WINDOW", "60")),
    block_duration=int(os.getenv("RATE_LIMIT_BLOCK", "300")),
    key_prefix="rate:tenant",
)

# Vitrine (loja pública): login 5/min, cadastro 3/min, checkout 10/min
loja_login_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("LOJA_LOGIN_RATE_LIMIT_MAX", "5")),
    window_seconds=60,
    block_duration=300,
    key_prefix="rate:loja_login",
)
loja_cadastro_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("LOJA_CADASTRO_RATE_LIMIT_MAX", "3")),
    window_seconds=60,
    block_duration=300,
    key_prefix="rate:loja_cadastro",
)
loja_checkout_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("LOJA_CHECKOUT_RATE_LIMIT_MAX", "10")),
    window_seconds=60,
    block_duration=300,
    key_prefix="rate:loja_checkout",
)
loja_pedido_consultar_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("LOJA_PEDIDO_CONSULTAR_RATE_LIMIT_MAX", "15")),
    window_seconds=60,
    block_duration=300,
    key_prefix="rate:loja_pedido_consultar",
)
loja_nova_tentativa_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("LOJA_NOVA_TENTATIVA_RATE_LIMIT_MAX", "5")),
    window_seconds=300,
    block_duration=600,
    key_prefix="rate:loja_nova_tentativa",
)

# Vitrine pública (HTML /, /index.html, /loja): limite mais alto para navegação legítima
loja_public_page_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("LOJA_PUBLIC_RATE_LIMIT_MAX", "600")),
    window_seconds=int(os.getenv("LOJA_PUBLIC_RATE_LIMIT_WINDOW", "60")),
    block_duration=int(os.getenv("LOJA_PUBLIC_RATE_LIMIT_BLOCK", "60")),
    key_prefix="rate:loja_public_page",
)

# Esqueci minha senha: solicitar reset (3 req / 15 min) e redefinir com token (5 req / 15 min)
forgot_password_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("FORGOT_PASSWORD_RATE_LIMIT_MAX", "3")),
    window_seconds=int(os.getenv("FORGOT_PASSWORD_RATE_LIMIT_WINDOW", "900")),
    block_duration=int(os.getenv("FORGOT_PASSWORD_RATE_LIMIT_BLOCK", "600")),
    key_prefix="rate:forgot_password",
)
reset_password_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("RESET_PASSWORD_RATE_LIMIT_MAX", "5")),
    window_seconds=900,
    block_duration=600,
    key_prefix="rate:reset_password",
)

# Webhooks de pagamento: limite por IP (evitar abuso/DDoS)
webhook_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("WEBHOOK_RATE_LIMIT_MAX", "120")),
    window_seconds=60,
    block_duration=60,
    key_prefix="rate:webhook",
)

async def check_rate_limit(request: Request) -> None:
    """
    Middleware para verificar rate limiting
    
    Raises:
        HTTPException: Se o rate limit for excedido
    """
    client_ip = get_client_ip(request)
    
    # Verificar rate limit (em thread para não bloquear event loop - Redis síncrono)
    allowed, error_message = await asyncio.to_thread(rate_limiter.is_allowed, client_ip)
    
    if not allowed:
        log_error(f"Rate limit excedido para IP {client_ip}: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": error_message,
                "retry_after": 60
            }
        )

async def check_login_rate_limit(request: Request) -> None:
    """Rate limit mais restritivo para login"""
    client_ip = get_client_ip(request)
    allowed, error_message = await asyncio.to_thread(login_rate_limiter.is_allowed, client_ip)

    if not allowed:
        log_error(f"Rate limit de login excedido para IP {client_ip}: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": error_message,
                "retry_after": 60
            }
        )

async def check_register_rate_limit(request: Request) -> None:
    """Rate limit para cadastro público (menos requisições por janela maior)."""
    client_ip = get_client_ip(request)
    allowed, error_message = await asyncio.to_thread(register_rate_limiter.is_allowed, client_ip)
    if not allowed:
        log_error(f"Rate limit de cadastro excedido para IP {client_ip}: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "Rate limit exceeded", "message": error_message, "retry_after": 60},
        )

async def check_loja_login_rate_limit(request: Request) -> None:
    """Rate limit para POST /loja/login (5/min por IP)."""
    client_ip = get_client_ip(request)
    allowed, _ = await asyncio.to_thread(loja_login_rate_limiter.is_allowed, client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente em alguns minutos.",
            headers={"Retry-After": "60"},
        )


async def check_loja_cadastro_rate_limit(request: Request) -> None:
    """Rate limit para POST /loja/cadastro (3/min por IP)."""
    client_ip = get_client_ip(request)
    allowed, _ = await asyncio.to_thread(loja_cadastro_rate_limiter.is_allowed, client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de cadastro. Tente novamente em alguns minutos.",
            headers={"Retry-After": "60"},
        )


async def check_forgot_password_rate_limit(request: Request) -> None:
    """Rate limit para solicitar redefinição de senha (ex.: 3 req / 15 min por IP)."""
    client_ip = get_client_ip(request)
    allowed, error_message = await asyncio.to_thread(forgot_password_rate_limiter.is_allowed, client_ip)
    if not allowed:
        log_error(f"Rate limit forgot-password excedido para IP {client_ip}: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas solicitações. Tente novamente em alguns minutos.",
            headers={"Retry-After": "60"},
        )


async def check_reset_password_rate_limit(request: Request) -> None:
    """Rate limit para POST redefinir-senha (ex.: 5 req / 15 min por IP)."""
    client_ip = get_client_ip(request)
    allowed, _ = await asyncio.to_thread(reset_password_rate_limiter.is_allowed, client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Tente novamente em alguns minutos.",
            headers={"Retry-After": "60"},
        )


async def check_loja_checkout_rate_limit(request: Request) -> None:
    """Rate limit para POST /loja/checkout (10/min por IP)."""
    client_ip = get_client_ip(request)
    allowed, _ = await asyncio.to_thread(loja_checkout_rate_limiter.is_allowed, client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas requisições de checkout. Tente novamente em alguns minutos.",
            headers={"Retry-After": "60"},
        )


async def check_loja_pedido_consultar_rate_limit(request: Request) -> None:
    """Rate limit para GET /loja/pedido/consultar (anti-enumeração)."""
    client_ip = get_client_ip(request)
    allowed, _ = await asyncio.to_thread(loja_pedido_consultar_rate_limiter.is_allowed, client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas consultas. Tente novamente em alguns minutos.",
            headers={"Retry-After": "60"},
        )


async def check_loja_nova_tentativa_rate_limit(request: Request) -> None:
    """Rate limit para POST /loja/pedidos/{id}/nova-tentativa-pagamento (5/5min quando não autenticado)."""
    client_ip = get_client_ip(request)
    allowed, _ = await asyncio.to_thread(loja_nova_tentativa_rate_limiter.is_allowed, client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas. Tente novamente em alguns minutos.",
            headers={"Retry-After": "300"},
        )


async def check_loja_public_page_rate_limit(request: Request) -> None:
    """Rate limit para páginas públicas da vitrine (tráfego alto/normal de navegação)."""
    client_ip = get_client_ip(request)
    allowed, error_message = await asyncio.to_thread(loja_public_page_rate_limiter.is_allowed, client_ip)
    if not allowed:
        log_error(f"Rate limit vitrine pública excedido para IP {client_ip}: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": error_message,
                "retry_after": 60,
            },
        )


geo_rate_limiter = RedisRateLimiter(
    max_requests=int(os.getenv("GEO_RATE_LIMIT_MAX", "30")),
    window_seconds=int(os.getenv("GEO_RATE_LIMIT_WINDOW", "60")),
    block_duration=int(os.getenv("GEO_RATE_LIMIT_BLOCK", "120")),
    key_prefix="rate:geo",
)


async def check_geo_rate_limit(request: Request) -> None:
    """Rate limit para endpoints de geolocalização pública (30/min por IP)."""
    client_ip = get_client_ip(request)
    allowed, error_message = await asyncio.to_thread(geo_rate_limiter.is_allowed, client_ip)
    if not allowed:
        log_error(f"Rate limit geo excedido para IP {client_ip}: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": error_message,
                "retry_after": 60,
            },
        )


async def check_webhook_rate_limit(request: Request) -> None:
    """Rate limit para POST /api/webhooks/* (ex.: 120/min por IP)."""
    client_ip = get_client_ip(request)
    allowed, _ = await asyncio.to_thread(webhook_rate_limiter.is_allowed, client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas requisições. Tente novamente em alguns minutos.",
            headers={"Retry-After": "60"},
        )


def get_client_ip(request: Request) -> str:
    """Obtém o IP real do cliente considerando proxies"""
    # Verificar headers de proxy
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Pegar o primeiro IP da lista
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # IP direto
    return request.client.host if request.client else "unknown" 