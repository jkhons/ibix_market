# PDV Ibix - Middleware de Autenticação
import time
from typing import List, Optional, Tuple

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload, selectinload

from ..database.connection import get_db
from ..models import Permissao, Role, RolePermissao, Usuario
from .auth import AuthConfig
from .logging import log_security
from .scope import ClienteScope, get_cliente_scope


# Cache em memória para permissões (TTL 5 min) - reduz queries repetidas na mesma sessão
class PermissionCache:
    _cache: dict = {}
    _ttl: int = 300  # segundos

    @classmethod
    def get(cls, user_id: int) -> Optional[List[str]]:
        if user_id in cls._cache:
            data, timestamp = cls._cache[user_id]
            if time.time() - timestamp < cls._ttl:
                return data
            del cls._cache[user_id]
        return None

    @classmethod
    def set(cls, user_id: int, data: List[str]) -> None:
        cls._cache[user_id] = (data, time.time())

    @classmethod
    def invalidate(cls, user_id: Optional[int] = None) -> None:
        """Invalida cache para user_id ou todo o cache se user_id for None."""
        if user_id is not None:
            cls._cache.pop(user_id, None)
        else:
            cls._cache.clear()

# Bearer token para autenticação
security = HTTPBearer()
# Security opcional (não lança erro se token ausente)
security_optional = HTTPBearer(auto_error=False)

def _get_token_from_request(request: Request) -> Optional[str]:
    """Token do header Authorization Bearer ou do cookie pdv_solumatica_token/pdv_automscale_token."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return request.cookies.get("pdv_solumatica_token") or request.cookies.get("pdv_automscale_token")


class AuthMiddleware:
    """Middleware de autenticação e autorização"""

    @staticmethod
    async def get_current_user(
        request: Request,
        db: Session = Depends(get_db),
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    ) -> Usuario:
        """Obtém usuário atual a partir do token JWT (header Authorization ou cookie pdv_solumatica_token)."""
        token = None
        if credentials and credentials.credentials:
            token = credentials.credentials
        if not token:
            token = _get_token_from_request(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token não informado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            payload = AuthConfig.verify_token(token)
            user_id = payload.get("sub")
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Buscar usuário no banco (com role carregada para checagens de permissão)
            user = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == int(user_id)).first()
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário não encontrado",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not user.ativo:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário inativo",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            from app.core.rls import resolve_rls_bypass_for_role, sync_rls_from_request_context
            from app.core.scope import resolve_tenant_pagador
            from app.core.request_context import update_request_context

            brand = getattr(getattr(request, "state", None), "brand", None)
            brand_id_val = getattr(brand, "id", None) if brand else None
            role_nome = user.role.nome if user.role else None
            tenant_id = resolve_tenant_pagador(db, user.id, role_nome)
            update_request_context(
                user_id=user.id,
                tenant_id=tenant_id,
                brand_id=brand_id_val,
                bypass_rls=resolve_rls_bypass_for_role(role_nome),
            )
            sync_rls_from_request_context(db)
            
            return user

        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Erro de autenticação",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    async def get_current_active_user(
        current_user: Usuario = Depends(get_current_user)
    ) -> Usuario:
        """Verifica se o usuário está ativo"""
        if not current_user.ativo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuário inativo"
            )
        return current_user
    
    @staticmethod
    def require_role(required_roles: List[str]):
        """Decorator para verificar roles específicas"""
        def role_checker(current_user: Usuario = Depends(AuthMiddleware.get_current_user)):
            if not current_user.role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuário sem role definida"
                )
            
            user_role = current_user.role.nome if current_user.role else None
            if user_role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Acesso negado. Role necessária: {', '.join(required_roles)}"
                )
            
            return current_user
        return role_checker
    
    @staticmethod
    def require_permission(required_permission: str):
        """Decorator para verificar permissão específica. Usa PermissionCache para evitar query em toda chamada."""
        def permission_checker(
            current_user: Usuario = Depends(AuthMiddleware.get_current_user),
            db: Session = Depends(get_db),
        ):
            if not current_user.role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuário sem role definida"
                )
            if current_user.role.nome == "Superadministrador":
                return current_user
            perms = get_user_permissions(current_user.id, db)
            if required_permission not in perms:
                log_security("permission_denied", ip="", user=str(current_user.id), details=required_permission)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permissão necessária: {required_permission}"
                )
            return current_user
        return permission_checker
    
    @staticmethod
    async def get_current_user_cliente(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Optional[int]:
        """
        Obtém o cliente_id do token JWT do usuário atual.
        Retorna None se o usuário não for vinculado a um cliente.
        """
        try:
            # Verificar e decodificar token
            payload = AuthConfig.verify_token(credentials.credentials)
            # Extrair cliente_id do payload (pode ser None)
            cliente_id = payload.get("cliente_id")
            
            if cliente_id is not None:
                return int(cliente_id)
            
            return None
            
        except Exception:
            # Em caso de erro, retornar None (usuário pode não ter cliente)
            return None
    
    @staticmethod
    async def require_cliente_access(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> int:
        """
        Garante que o usuário tem cliente_id no token.
        Retorna o cliente_id ou levanta HTTPException 403 se não houver.
        """
        cliente_id = await AuthMiddleware.get_current_user_cliente(credentials)
        
        if cliente_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado. Usuário não vinculado a cliente."
            )
        
        return cliente_id

# Funções de conveniência (referência direta para Depends injetar o Usuario, não o callable)
get_current_user = AuthMiddleware.get_current_user

def get_current_active_user():
    """Dependency para obter usuário ativo"""
    return AuthMiddleware.get_current_active_user

def require_admin():
    """Dependency para verificar se é administrador"""
    return AuthMiddleware.require_role(["Administrador"])

def require_superadmin():
    """Dependency para verificar se é Superadministrador (Saas.md Fase 2)"""
    return AuthMiddleware.require_role(["Superadministrador"])

def require_superadmin_or_admin():
    """Dependency para Superadministrador ou Administrador"""
    return AuthMiddleware.require_role(["Superadministrador", "Administrador"])

def require_cliente_administrador():
    """Dependency para Cliente Administrador (Saas.md Fase 6.2 - Minha equipe)"""
    return AuthMiddleware.require_role(["Cliente Administrador"])


def require_superadmin_or_admin_or_cliente_admin():
    """Dependency para Superadministrador, Administrador ou Cliente Administrador (ex.: config e-mail por cliente)."""
    return AuthMiddleware.require_role(["Superadministrador", "Administrador", "Cliente Administrador"])

def require_technician():
    """Dependency para verificar se é técnico"""
    return AuthMiddleware.require_role(["Administrador", "Técnico"])

def require_client():
    """Dependency para verificar se é subcliente (role Subcliente)"""
    return AuthMiddleware.require_role(["Subcliente"])

def require_permission(permission: str):
    """Dependency para verificar permissão específica"""
    return AuthMiddleware.require_permission(permission)

async def get_current_user_cliente(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
) -> Optional[int]:
    """Dependency para obter cliente_id do token"""
    try:
        if not credentials:
            return None
        return await AuthMiddleware.get_current_user_cliente(credentials)
    except Exception:
        # Se houver erro ao obter cliente_id, retornar None (usuário pode não ter cliente)
        return None


def get_cliente_scope_dep(
    request: Request,
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    db: Session = Depends(get_db),
    cliente_id_token: Optional[int] = Depends(get_current_user_cliente),
) -> ClienteScope:
    """Dependency que retorna ClienteScope para o usuário atual (Saas.md Fase 3)."""
    role_nome = current_user.role.nome if current_user.role else None
    scope = get_cliente_scope(db, current_user.id, role_nome, cliente_id_token)
    from app.services.brand_scope_service import apply_host_brand_cliente_scope

    return apply_host_brand_cliente_scope(request, db, scope)


def get_subcliente_scope_or_404_dep(
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    db: Session = Depends(get_db),
    cliente_id_token: Optional[int] = Depends(get_current_user_cliente),
) -> ClienteScope:
    """Dependency para rotas do Portal Subcliente: exige role Subcliente e escopo não vazio; senão 403/404."""
    if not current_user.role or current_user.role.nome != "Subcliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito ao Portal Subcliente.",
        )
    scope = get_cliente_scope(db, current_user.id, current_user.role.nome, cliente_id_token)
    if not scope.allowed_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum cliente vinculado. Entre em contato com o administrador.",
        )
    return scope


async def require_cliente_access(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    """Dependency para garantir que usuário tem cliente_id no token"""
    return await AuthMiddleware.require_cliente_access(credentials)

# Roles que podem acessar APIs "admin" mesmo tendo cliente_id no token (ex.: Cliente Administrador)
ROLES_COM_ACESSO_ADMIN = ("Superadministrador", "Administrador", "Cliente Administrador")


async def forbid_cliente_access(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
) -> None:
    """Bloqueia acesso apenas para usuários da área do cliente (Subcliente/Cliente).
    Cliente Administrador, Administrador e Superadministrador têm acesso conforme role_permissoes.
    """
    try:
        if not credentials:
            return None
        payload = AuthConfig.verify_token(credentials.credentials)
        role = payload.get("role")
        if role in ROLES_COM_ACESSO_ADMIN:
            return None
        if payload.get("cliente_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado para usuário cliente."
            )
        return None
    except HTTPException:
        raise
    except Exception:
        return None


def forbid_contador_edit(current_user: Usuario = Depends(AuthMiddleware.get_current_user)) -> None:
    """Bloqueia Contador de editar/cancelar notas fiscais (apenas visualização e exportação)."""
    if current_user.role and current_user.role.nome == "Contador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contador não pode editar ou cancelar documentos fiscais.",
        )
    return None


# Função para verificação de autenticação em rotas HTML
async def check_auth_for_html(request: Request, db: Session = Depends(get_db)):
    """Verifica autenticação para rotas HTML e redireciona se necessário.
    Reutiliza request.state.user_payload quando preenchido pelo middleware add_user_to_request."""
    from fastapi.responses import RedirectResponse
    try:
        # Reutilizar payload já verificado pelo middleware (evita re-verificar token)
        if getattr(request.state, "user_payload", None) and getattr(request.state, "user_id", None):
            return None
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        if not token:
            token = request.cookies.get("pdv_solumatica_token") or request.cookies.get("pdv_automscale_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return RedirectResponse(url="/login", status_code=302)
        request.state.user_id = int(user_id)
        request.state.user_payload = payload
        return None
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

def get_user_with_permissions(user_id: int, db: Session) -> Tuple[Optional[Usuario], List[str]]:
    """Carrega usuário com role e permissões em uma única query (eager load).
    Retorna (user, permissions_list). Evita N+1 e duplicação de query de Usuario."""
    try:
        user = db.query(Usuario).options(
            selectinload(Usuario.role).selectinload(Role.role_permissoes).selectinload(RolePermissao.permissao)
        ).filter(Usuario.id == user_id).first()
        if not user:
            return None, []
        if not user.role:
            return user, []
        if user.role.nome == "Superadministrador":
            todas = db.query(Permissao).filter(Permissao.ativo == True).all()
            modulos = list(set([p.modulo for p in todas]))
            nomes = [p.nome for p in todas]
            return user, modulos + nomes
        permissoes = [rp.permissao for rp in user.role.role_permissoes if rp.permissao and rp.permissao.ativo]
        modulos = list(set([p.modulo for p in permissoes]))
        nomes = [p.nome for p in permissoes]
        return user, modulos + nomes
    except Exception as e:
        print(f"❌ Erro ao obter usuário/permissões {user_id}: {e}")
        return None, []


def get_user_permissions(user_id: int, db: Session) -> List[str]:
    """Obtém as permissões do usuário (módulos e nomes completos das permissões).
    Usa cache Redis (TTL 5 min) com fallback para memória; get_user_with_permissions para carga."""
    from .redis_cache import get_permissions_cached

    def fetch() -> List[str]:
        _, perms = get_user_with_permissions(user_id, db)
        return perms

    try:
        return get_permissions_cached(user_id, fetch)
    except Exception:
        cached = PermissionCache.get(user_id)
        if cached is not None:
            return cached
        _, perms = get_user_with_permissions(user_id, db)
        PermissionCache.set(user_id, perms)
        return perms 