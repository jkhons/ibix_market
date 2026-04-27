# PDV Ibix - Rotas de Autenticação
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...core.audit import audit_action
from ...core.logging import log_error, log_security
from ...core.middleware import AuthMiddleware, require_admin, require_permission
from ...core.rate_limiter import (
    check_forgot_password_rate_limit,
    check_login_rate_limit,
    check_register_rate_limit,
    check_reset_password_rate_limit,
)
from ...database.connection import get_db
from ...models import Role, Usuario
from ...schemas.auth import (
    ForgotPasswordRequest,
    LoginResponse,
    LogoutResponse,
    PasswordChange,
    RegisterInfluencerRequest,
    RegisterPublicRequest,
    RegisterRepresentanteRequest,
    ResetPasswordRequest,
    UserLogin,
    UserRegister,
    UserResponse,
)
from ...services.auth_service import AuthService
from ...services.password_reset_service import (
    request_reset_pdv,
    reset_password_pdv,
    validate_token_pdv,
)

router = APIRouter(prefix="/auth", tags=["Autenticação"])

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    """Endpoint para login do usuário"""
    try:
        await check_login_rate_limit(request)

        # Realizar login
        client = getattr(request, "client", None)
        ip = getattr(client, "host", "") if client else ""
        token = AuthService.login_user(db, login_data, ip=ip)
        
        # Buscar dados do usuário
        user = AuthService.get_user_by_id(db, token.user_id)
        
        # Criar resposta do usuário
        user_response = UserResponse(
            id=user.id,
            nome=user.nome,
            email=user.email,
            cargo=user.cargo,
            ativo=user.ativo,
            role_id=user.role_id,
            role_nome=user.role.nome if user.role else None,
            created_at=user.created_at.isoformat() if user.created_at else None,
            updated_at=user.updated_at.isoformat() if user.updated_at else None
        )
        
        # Criar resposta
        response_data = LoginResponse(
            success=True,
            message="Login realizado com sucesso",
            token=token,
            user=user_response
        )
        
        
        # Sempre salvar token em cookie para requisições HTML
        from fastapi.responses import JSONResponse
        try:
            content = response_data.model_dump()
        except AttributeError:
            content = response_data.dict()
        response = JSONResponse(content=content)

        # Secure=True quando a requisição veio por HTTPS (produção atrás de proxy)
        is_https = (
            os.getenv("HTTPS", "").lower() == "true"
            or (request.url.scheme == "https" or (request.headers.get("x-forwarded-proto") or "").strip().lower() == "https")
        )
        response.set_cookie(
            key="pdv_solumatica_token",
            value=token.access_token,
            httponly=False,
            secure=is_https,
            samesite="lax",
            max_age=28800,
            path="/"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("Erro no login", exc_info=e)
        return LoginResponse(
            success=False,
            message="Erro ao processar login"
        )

@router.post("/login/mobile", response_model=LoginResponse)
@router.post("/token", response_model=LoginResponse)  # Alias para compatibilidade OAuth2
async def login_mobile(
    request: Request,
    username: str = Form(..., description="Email do usuário"),
    password: str = Form(..., description="Senha do usuário"),
    db: Session = Depends(get_db),
):
    """
    Endpoint de login compatível com aplicativos mobile
    Aceita dados via application/x-www-form-urlencoded
    
    - **username**: Email do usuário (enviado como 'username' para compatibilidade OAuth2)
    - **password**: Senha do usuário
    """
    try:
        
        # Criar objeto UserLogin a partir dos dados do form
        login_data = UserLogin(email=username, password=password)
        
        # Realizar login
        client = getattr(request, "client", None)
        ip = getattr(client, "host", "") if client else ""
        token = AuthService.login_user(db, login_data, ip=ip)
        
        # Buscar dados do usuário
        user = AuthService.get_user_by_id(db, token.user_id)
        
        # Criar resposta do usuário
        user_response = UserResponse(
            id=user.id,
            nome=user.nome,
            email=user.email,
            cargo=user.cargo,
            ativo=user.ativo,
            role_id=user.role_id,
            role_nome=user.role.nome if user.role else None,
            created_at=user.created_at.isoformat() if user.created_at else None,
            updated_at=user.updated_at.isoformat() if user.updated_at else None
        )
        
        # Criar resposta
        response_data = LoginResponse(
            success=True,
            message="Login realizado com sucesso",
            token=token,
            user=user_response
        )
        
        
        # Para mobile, não precisamos de cookie, apenas retornar JSON puro
        from fastapi.responses import JSONResponse
        response = JSONResponse(content=response_data.dict())
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("Erro no login mobile", exc_info=e)
        return LoginResponse(
            success=False,
            message="Erro ao processar login mobile"
        )

@router.post("/register/public")
async def register_public(
    request: Request,
    data: RegisterPublicRequest,
    db: Session = Depends(get_db),
):
    """Cadastro público: cria empresa (Cliente) + usuário Cliente Administrador (Saas.md Fase 6).
    Rate limit aplicado (check_register_rate_limit). Recomendado: CAPTCHA e confirmação de e-mail (Saas.md 3.5)."""
    await check_register_rate_limit(request)
    try:
        user = AuthService.register_public(db, data)
        return {
            "message": "Cadastro realizado. Faça login para acessar.",
            "user_id": user.id,
            "email": user.email,
        }
    except HTTPException as he:
        detail_str = he.detail if isinstance(he.detail, str) else str(he.detail)
        log_error(f"Cadastro público rejeitado: status={he.status_code} detail={detail_str}")
        raise
    except Exception as e:
        log_error("Erro no cadastro público", exc_info=e)
        detail = str(e) if os.getenv("DEBUG", "").lower() in ("true", "1") else "Erro ao concluir cadastro. Tente novamente."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": detail},
        )


@router.post("/register/representante")
async def register_representante(
    request: Request,
    data: RegisterRepresentanteRequest,
    db: Session = Depends(get_db),
):
    """Cadastro público do Representante (Administrador): cria usuário com role Administrador.
    Rate limit aplicado (check_register_rate_limit)."""
    await check_register_rate_limit(request)
    try:
        user = AuthService.register_representante(db, data)
        return {
            "message": "Cadastro realizado. Faça login para acessar.",
            "user_id": user.id,
            "email": user.email,
        }
    except HTTPException as he:
        detail_str = he.detail if isinstance(he.detail, str) else str(he.detail)
        log_error(f"Cadastro representante rejeitado: status={he.status_code} detail={detail_str}")
        raise
    except Exception as e:
        log_error("Erro no cadastro representante", exc_info=e)
        detail = str(e) if os.getenv("DEBUG", "").lower() in ("true", "1") else "Erro ao concluir cadastro. Tente novamente."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": detail},
        )


@router.post("/register/influencer")
async def register_influencer(
    request: Request,
    data: RegisterInfluencerRequest,
    db: Session = Depends(get_db),
):
    """Cadastro publico do Influencer: cria usuario com role Influencer + divulgador.
    Rate limit aplicado."""
    await check_register_rate_limit(request)
    try:
        user = AuthService.register_influencer(db, data)
        return {
            "message": "Cadastro recebido! Vamos analisar seu perfil em até 48h.",
            "user_id": user.id,
            "email": user.email,
        }
    except HTTPException as he:
        detail_str = he.detail if isinstance(he.detail, str) else str(he.detail)
        log_error(f"Cadastro influencer rejeitado: status={he.status_code} detail={detail_str}")
        raise
    except Exception as e:
        log_error("Erro no cadastro influencer", exc_info=e)
        detail = str(e) if os.getenv("DEBUG", "").lower() in ("true", "1") else "Erro ao concluir cadastro. Tente novamente."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": detail},
        )


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """Endpoint para registro de usuário (apenas administradores)"""
    try:
        user = AuthService.create_user(db, user_data)
        audit_action(
            db,
            "usuario_criado",
            user_id=current_user.id,
            tenant_id=getattr(current_user, "tenant_id", None),
            recurso_tipo="usuario",
            recurso_id=user.id,
            detalhes=f"email={user.email}",
        )
        return UserResponse(
            id=user.id,
            nome=user.nome,
            email=user.email,
            cargo=user.cargo,
            ativo=user.ativo,
            role_id=user.role_id,
            role_nome=user.role.nome if user.role else None,
            created_at=user.created_at.isoformat() if user.created_at else None,
            updated_at=user.updated_at.isoformat() if user.updated_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar usuário: {str(e)}"
        )

def _get_token_from_request(request: Request) -> Optional[str]:
    """Token do header Authorization Bearer ou do cookie pdv_solumatica_token."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return request.cookies.get("pdv_solumatica_token") if request else None


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
):
    """Endpoint para logout do usuário. Invalida o token na blacklist Redis."""
    client = getattr(request, "client", None)
    ip = getattr(client, "host", "") if client else ""
    log_security("logout", ip=ip, user=str(current_user.id), details="")
    token = _get_token_from_request(request)
    if token:
        from jose import jwt

        from ...core.auth import ALGORITHM, SECRET_KEY
        from ...core.redis_cache import add_token_to_blacklist
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                import time
                ttl = max(0, int(exp) - int(time.time()))
                add_token_to_blacklist(jti, ttl)
        except Exception:
            pass

    response_data = LogoutResponse(
        success=True,
        message="Logout realizado com sucesso"
    )

    if "text/html" in (request.headers.get("accept") or ""):
        from fastapi.responses import JSONResponse
        response = JSONResponse(content=response_data.dict())
        response.delete_cookie(key="pdv_solumatica_token")
        return response

    return response_data

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    ⚡ OTIMIZADO: Endpoint para obter informações do usuário atual
    Usa dados do token JWT em vez de consultar o banco a cada requisição
    """
    try:
        # Obter token do header ou cookie
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        
        if not token:
            token = request.cookies.get("pdv_solumatica_token")
        
        if not token:
            raise HTTPException(status_code=401, detail="Token não encontrado")
        
        # Decodificar token (sem consultar banco)
        from ...core.auth import AuthConfig
        payload = AuthConfig.verify_token(token)
        
        # Extrair dados do token (já contém user_id, email, role)
        user_id = int(payload.get("sub"))
        email = payload.get("email")
        role_nome = payload.get("role")
        
        # ⚡ OTIMIZAÇÃO: Apenas buscar dados adicionais se necessário
        # Para usuários logados, usar dados do token JWT
        # Apenas consultar banco se precisar de dados que não estão no token
        
        # Consulta rápida e específica (apenas os campos necessários)
        user = db.query(Usuario.id, Usuario.nome, Usuario.cargo, Usuario.ativo, 
                       Usuario.role_id, Usuario.created_at, Usuario.updated_at).filter(
            Usuario.id == user_id
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        return UserResponse(
            id=user.id,
            nome=user.nome,
            email=email,  # Do token
            cargo=user.cargo,
            ativo=user.ativo,
            role_id=user.role_id,
            role_nome=role_nome,  # Do token
            created_at=user.created_at.isoformat() if user.created_at else None,
            updated_at=user.updated_at.isoformat() if user.updated_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Erro ao obter usuário: {str(e)}")

MESSAGE_FORGOT_PASSWORD = (
    "Se este e-mail estiver cadastrado, você receberá um link para redefinir sua senha."
)


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Solicita redefinição de senha (Esqueci minha senha). Resposta sempre igual para não revelar se o e-mail existe."""
    await check_forgot_password_rate_limit(request)
    base_url = str(request.base_url).rstrip("/")
    request_reset_pdv(db, body.email, base_url=base_url)
    return {"message": MESSAGE_FORGOT_PASSWORD}


@router.get("/redefinir-senha/valida")
async def redefinir_senha_valida(
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Verifica se o token de redefinição é válido (para o front exibir formulário ou erro)."""
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token ausente.")
    valid = validate_token_pdv(db, token)
    return {"valid": valid}


@router.post("/redefinir-senha")
async def redefinir_senha(
    request: Request,
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Redefine a senha usando o token enviado por e-mail."""
    await check_reset_password_rate_limit(request)
    success, error_msg = reset_password_pdv(db, body.token, body.new_password, body.confirm_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    return {"message": "Senha alterada com sucesso. Faça login com a nova senha."}


@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: Usuario = Depends(AuthMiddleware.get_current_user),
    db: Session = Depends(get_db),
):
    """Endpoint para alterar senha do usuário"""
    # Verificar se as senhas coincidem
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="As senhas não coincidem"
        )
    
    # Alterar senha
    success = AuthService.change_password(
        db, 
        current_user.id, 
        password_data.current_password, 
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta"
        )
    ip = (request.client.host if request and getattr(request, "client", None) else "") or ""
    log_security("senha_alterada", ip=ip, user=str(current_user.id), details="")
    return {"message": "Senha alterada com sucesso"}

@router.get("/users", response_model=List[UserResponse])
async def get_users(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """Endpoint para listar usuários (apenas administradores)"""
    try:
        users = db.query(Usuario).all()
        return [
            UserResponse(
                id=user.id,
                nome=user.nome,
                email=user.email,
                cargo=user.cargo,
                ativo=user.ativo,
                role_id=user.role_id,
                role_nome=user.role.nome if user.role else None,
                created_at=user.created_at.isoformat() if user.created_at else None,
                updated_at=user.updated_at.isoformat() if user.updated_at else None
            )
            for user in users
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar usuários: {str(e)}"
        )

# Roles que o Cliente Administrador pode atribuir (apenas hierarquia abaixo)
ROLES_PERMITIDAS_CLIENTE_ADMIN = ("Técnico", "Subcliente")


@router.get("/roles")
async def get_roles(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("usuarios:visualizar"))
):
    """Listar roles. Superadmin/Administrador: todas. Cliente Administrador: apenas Técnico e Subcliente."""
    roles = db.query(Role).filter(Role.ativo == True).all()
    # Cliente Administrador só pode criar/editar usuários com função Técnico ou Subcliente
    if current_user.role and current_user.role.nome == "Cliente Administrador":
        roles = [r for r in roles if r.nome in ROLES_PERMITIDAS_CLIENTE_ADMIN]
    return [
        {
            "id": role.id,
            "nome": role.nome,
            "descricao": role.descricao,
            "ativo": role.ativo
        }
        for role in roles
    ]

@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """Endpoint para ativar usuário (apenas administradores)"""
    try:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user.ativo = True
        db.commit()
        audit_action(
            db,
            "usuario_ativado",
            user_id=current_user.id,
            tenant_id=getattr(current_user, "tenant_id", None),
            recurso_tipo="usuario",
            recurso_id=user_id,
        )
        return {"message": f"Usuário {user.nome} ativado com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao ativar usuário: {str(e)}"
        )

@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """Endpoint para desativar usuário (apenas administradores)"""
    try:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        user.ativo = False
        db.commit()
        audit_action(
            db,
            "usuario_desativado",
            user_id=current_user.id,
            tenant_id=getattr(current_user, "tenant_id", None),
            recurso_tipo="usuario",
            recurso_id=user_id,
        )
        return {"message": f"Usuário {user.nome} desativado com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao desativar usuário: {str(e)}"
        ) 