# PDV Ibix - Schemas de Autenticação
from typing import Optional

from pydantic import BaseModel, EmailStr, ValidationInfo, field_validator


class UserLogin(BaseModel):
    """Schema para login do usuário"""
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    """Schema para registro de usuário"""
    nome: str
    email: EmailStr
    password: str
    cargo: str
    role_id: Optional[int] = None


class RegisterPublicRequest(BaseModel):
    """Schema para cadastro público (Saas.md Fase 6): cria empresa + Cliente Administrador."""
    nome: str
    email: EmailStr
    password: str
    confirm_password: str
    codigo_promocional: Optional[str] = None
    # Dados da empresa (cliente)
    nome_empresa: str
    cnpj: str
    cep: Optional[str] = None
    endereco: str
    cidade: str
    uf: str
    contato: str
    telefone: str

    @field_validator("confirm_password")
    @classmethod
    def senhas_coincidem(cls, v: str, info: ValidationInfo) -> str:
        if info.data and "password" in info.data and v != info.data.get("password"):
            raise ValueError("As senhas não coincidem")
        return v


class RegisterRepresentanteRequest(BaseModel):
    """Schema para cadastro público do Representante (Administrador): apenas usuário com role Administrador."""
    nome: str
    email: EmailStr
    password: str
    confirm_password: str
    telefone: Optional[str] = None

    @field_validator("confirm_password")
    @classmethod
    def senhas_coincidem(cls, v: str, info: ValidationInfo) -> str:
        if info.data and "password" in info.data and v != info.data.get("password"):
            raise ValueError("As senhas não coincidem")
        return v


class RegisterInfluencerRequest(BaseModel):
    """Schema para cadastro publico do Influencer: cria usuario com role Influencer + divulgador."""
    nome: str
    email: EmailStr
    password: str
    confirm_password: str
    telefone: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    nicho: Optional[str] = None
    redes_sociais: Optional[str] = None
    tipo_atuacao: Optional[str] = None
    bio: Optional[str] = None

    @field_validator("confirm_password")
    @classmethod
    def senhas_coincidem(cls, v: str, info: ValidationInfo) -> str:
        if info.data and "password" in info.data and v != info.data.get("password"):
            raise ValueError("As senhas não coincidem")
        return v


class Token(BaseModel):
    """Schema para token de acesso"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    email: str
    role: Optional[str] = None

class TokenData(BaseModel):
    """Schema para dados do token"""
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    """Schema para resposta de usuário"""
    id: int
    nome: str
    email: str
    cargo: str
    ativo: bool
    role_id: Optional[int] = None
    role_nome: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    """Schema para atualização de usuário"""
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    cargo: Optional[str] = None
    ativo: Optional[bool] = None
    role_id: Optional[int] = None

class PasswordChange(BaseModel):
    """Schema para alteração de senha"""
    current_password: str
    new_password: str
    confirm_password: str

class LoginResponse(BaseModel):
    """Schema para resposta de login"""
    success: bool
    message: str
    token: Optional[Token] = None
    user: Optional[UserResponse] = None

class LogoutResponse(BaseModel):
    """Schema para resposta de logout"""
    success: bool
    message: str


class ForgotPasswordRequest(BaseModel):
    """Schema para solicitar redefinição de senha (Esqueci minha senha)."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema para redefinir senha com token."""
    token: str
    new_password: str
    confirm_password: str