# PDV Ibix - Configurações de Autenticação
"""Auth unificada: usa exclusivamente app.core.config.settings para SECRET_KEY e ACCESS_TOKEN_EXPIRE_MINUTES."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Union

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Bearer token para autenticação
security = HTTPBearer()


def _to_bytes_password(password: str) -> bytes:
    """Trunca senha para 72 bytes (limite do bcrypt)."""
    b = password.encode("utf-8")
    return b[:72] if len(b) > 72 else b


def _to_bytes_hash(hashed_password: Union[str, bytes]) -> bytes:
    """Garante que o hash esteja em bytes."""
    if isinstance(hashed_password, bytes):
        return hashed_password
    return hashed_password.encode("utf-8")


class AuthConfig:
    """Configurações de autenticação (usa bcrypt diretamente, compatível com bcrypt 4.1+)."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifica se a senha está correta."""
        try:
            pwd_bytes = _to_bytes_password(plain_password)
            hash_bytes = _to_bytes_hash(hashed_password)
            return bcrypt.checkpw(pwd_bytes, hash_bytes)
        except Exception:
            return False

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Gera hash da senha."""
        pwd_bytes = _to_bytes_password(password)
        return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Cria token JWT de acesso"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> dict:
        """Verifica e decodifica token JWT. Rejeita tokens na blacklist (logout)."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            jti = payload.get("jti")
            if jti:
                from .redis_cache import is_token_blacklisted
                if is_token_blacklisted(jti):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token inválido (logout)",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            return payload
        except HTTPException:
            raise
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def get_current_user_from_token(token: str):
        """Obtém usuário atual a partir do token"""
        payload = AuthConfig.verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id

# Funções utilitárias
def create_user_token(user_id: int, email: str, role: str, cliente_id: Optional[int] = None) -> str:
    """Cria token para usuário. Inclui jti para blacklist no logout."""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "jti": str(uuid.uuid4()),
    }
    # Incluir cliente_id no token se fornecido
    if cliente_id is not None:
        token_data["cliente_id"] = cliente_id

    return AuthConfig.create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )

def create_consumidor_token(consumidor_id: int) -> str:
    """Token JWT para consumidor da loja (vitrine). Sem jti para não usar blacklist de logout PDV."""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {"sub": str(consumidor_id), "tipo": "consumidor"}
    return AuthConfig.create_access_token(data=token_data, expires_delta=access_token_expires)


def _hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_consumidor_refresh_token(
    db,
    consumidor_id: int,
    device_info: Optional[str] = None,
    commit: bool = True,
) -> Tuple[str, datetime]:
    """Gera refresh token opaco, persiste hash no DB, retorna (raw_token, expires_at)."""
    from app.models.consumidor_refresh_token import ConsumidorRefreshToken

    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_refresh_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.CONSUMIDOR_REFRESH_TOKEN_EXPIRE_DAYS)

    rt = ConsumidorRefreshToken(
        consumidor_id=consumidor_id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info=device_info,
    )
    db.add(rt)
    if commit:
        db.commit()
    else:
        db.flush()
    return raw_token, expires_at


def rotate_consumidor_refresh_token(
    db,
    raw_token: str,
    device_info: Optional[str] = None,
) -> Tuple[str, str, int]:
    """
    Valida refresh token, revoga o antigo, emite novo par (access + refresh).
    Retorna (new_access_token, new_raw_refresh, consumidor_id).
    Tudo em uma única transação. Lança HTTPException se inválido/expirado/revogado.
    """
    from app.models.consumidor_refresh_token import ConsumidorRefreshToken

    token_hash = _hash_refresh_token(raw_token)
    rt = db.query(ConsumidorRefreshToken).filter(ConsumidorRefreshToken.token_hash == token_hash).first()

    if not rt:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")
    if rt.revoked:
        _revoke_all_for_consumidor(db, rt.consumidor_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token já revogado (possível roubo)")
    expires_utc = rt.expires_at.replace(tzinfo=timezone.utc) if rt.expires_at.tzinfo is None else rt.expires_at
    if expires_utc < datetime.now(timezone.utc):
        rt.revoked = True
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expirado")

    rt.revoked = True

    new_access = create_consumidor_token(rt.consumidor_id)
    new_raw, _ = create_consumidor_refresh_token(db, rt.consumidor_id, device_info=device_info, commit=False)
    db.commit()
    return new_access, new_raw, rt.consumidor_id


def _revoke_all_for_consumidor(db, consumidor_id: int) -> None:
    from app.models.consumidor_refresh_token import ConsumidorRefreshToken
    db.query(ConsumidorRefreshToken).filter(
        ConsumidorRefreshToken.consumidor_id == consumidor_id,
        ConsumidorRefreshToken.revoked.is_(False),
    ).update({"revoked": True}, synchronize_session=False)
    db.commit()


def create_entregador_token(entregador_id: int, email: Optional[str] = None) -> str:
    """Token JWT para entregador (logística local). Sem jti. Payload: sub, tipo='entregador', email opcional."""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {"sub": str(entregador_id), "tipo": "entregador"}
    if email is not None:
        token_data["email"] = email
    return AuthConfig.create_access_token(data=token_data, expires_delta=access_token_expires)


def verify_user_credentials(email: str, password: str, hashed_password: str) -> bool:
    """Verifica credenciais do usuário"""
    if not email or not password:
        return False
    
    # Truncar senha para 72 bytes (limite do bcrypt)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    
    return AuthConfig.verify_password(password, hashed_password) 

# Função para obter usuário atual (compatibilidade com FastAPI)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtém usuário atual a partir do token de autorização"""
    try:
        payload = AuthConfig.verify_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"user_id": int(user_id), "email": payload.get("email"), "role": payload.get("role")}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) 