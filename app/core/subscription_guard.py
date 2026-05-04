# PDV Ibix - Guard de assinatura bloqueada (allowlist de rotas)
"""Quando o tenant está bloqueado (assinatura inadimplente após carência), o usuário
só pode acessar rotas na allowlist. Caso contrário: API retorna 403, HTML redireciona para /financeiro/assinatura."""

from typing import List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from ..database.connection import get_db
from ..models import Tenant, Usuario
from .middleware import AuthMiddleware
from .redis_cache import get_subscription_blocked_cached
from .scope import resolve_tenant_pagador

# Rotas que podem ser acessadas mesmo com assinatura bloqueada
SUBSCRIPTION_ALLOWLIST: List[str] = [
    "/financeiro/assinatura",
    "/api/v1/billing/my-subscription",
    "/api/v1/billing/pay-now",
    "/billing/success",
    "/billing/failure",
    "/billing/pending",
    "/auth/login",
    "/logout",
    "/static",
    "/api/v1/auth",
    "/entregas",  # Área do entregador (login e telas) — ator separado do tenant
    "/entregador",  # Redirects legados /entregador/* → /entregas*
]


def _path_in_allowlist(path: str) -> bool:
    """Verifica se o path está na allowlist (prefix match ou exato)."""
    path = path.rstrip("/") or "/"
    for allowed in SUBSCRIPTION_ALLOWLIST:
        if path == allowed or path.startswith(allowed.rstrip("/") + "/"):
            return True
    return False


def is_subscription_blocked(db: Session, user: Usuario) -> bool:
    """
    Retorna True se o tenant do usuário (resolve_tenant_pagador) estiver bloqueado.
    Considera Tenant.ativo = False como bloqueado. Sem tenant resolvido = não bloqueado.
    """
    role_nome = user.role.nome if user.role else None
    tenant_id = resolve_tenant_pagador(db, user.id, role_nome)
    if tenant_id is None:
        return False
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return False
    return tenant.ativo is False


def subscription_guard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
) -> None:
    """
    Dependency para rotas API: se o tenant do usuário estiver bloqueado e o path
    não estiver na allowlist, levanta HTTP 403.
    """
    path = request.url.path
    if _path_in_allowlist(path):
        return
    if is_subscription_blocked(db, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assinatura bloqueada. Realize o pagamento para continuar.",
        )


def check_subscription_redirect(request: Request, db: Session) -> Optional[RedirectResponse]:
    """
    Para rotas HTML: se o usuário estiver autenticado, tiver tenant bloqueado e o path
    não estiver na allowlist, retorna RedirectResponse para /financeiro/assinatura.
    Caso contrário retorna None (segue fluxo normal).
    """
    path = request.url.path
    if _path_in_allowlist(path):
        return None
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return None
    from ..models import Usuario
    user = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == user_id).first()
    if not user or not user.ativo:
        return None
    blocked = get_subscription_blocked_cached(
        user_id,
        lambda: is_subscription_blocked(db, user),
    )
    if not blocked:
        return None
    return RedirectResponse(url="/financeiro/assinatura", status_code=status.HTTP_302_FOUND)
