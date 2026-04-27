# PDV Ibix - Schemas para Usuários
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from ..utils.cpf_validator import CPFValidator
from .role import RoleResponse


class UsuarioBase(BaseModel):
    """Schema base para usuários"""
    nome: str = Field(..., min_length=2, max_length=255, description="Nome completo do usuário")
    email: EmailStr = Field(..., description="Email do usuário")
    cargo: Optional[str] = Field(None, min_length=2, max_length=100, description="Cargo (legacy - será removido)")
    ativo: bool = Field(default=False, description="Status ativo/inativo")
    cpf: Optional[str] = Field(None, max_length=14, description="CPF do usuário (opcional, formatado 000.000.000-00)")
    rg: Optional[str] = Field(None, max_length=20, description="RG do usuário (opcional)")
    documento_path: Optional[str] = Field(None, max_length=500, description="Caminho do documento/anexo (opcional)")

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, v: Optional[str]) -> Optional[str]:
        if not v or not str(v).strip():
            return None
        valido, formatado, erro = CPFValidator.validar_e_formatar(v)
        if not valido:
            raise ValueError(erro or "CPF inválido")
        return formatado

class UsuarioCreate(UsuarioBase):
    """Schema para criação de usuário"""
    senha: str = Field(..., min_length=6, description="Senha do usuário")
    role_id: int = Field(..., description="ID da função/role do usuário (obrigatório)")

class UsuarioClienteCreate(UsuarioBase):
    """Schema para criação de usuário vinculado a cliente"""
    senha: str = Field(..., min_length=6, description="Senha do usuário")
    cliente_id: int = Field(..., description="ID do cliente ao qual o usuário será vinculado")
    role_id: Optional[int] = Field(None, description="ID da função/role do usuário (opcional para usuários de cliente)")

class UsuarioUpdate(BaseModel):
    """Schema para atualização de usuário"""
    nome: Optional[str] = Field(None, min_length=2, max_length=255, description="Nome completo do usuário")
    email: Optional[EmailStr] = Field(None, description="Email do usuário")
    cargo: Optional[str] = Field(None, min_length=2, max_length=100, description="Cargo (legacy)")
    ativo: Optional[bool] = Field(None, description="Status ativo/inativo")
    senha: Optional[str] = Field(None, min_length=6, description="Nova senha do usuário")
    role_id: Optional[int] = Field(None, description="ID da função/role do usuário")
    cpf: Optional[str] = Field(None, max_length=14, description="CPF do usuário (opcional)")
    rg: Optional[str] = Field(None, max_length=20, description="RG do usuário (opcional)")
    documento_path: Optional[str] = Field(None, max_length=500, description="Caminho do documento/anexo (opcional)")
    contador_vinculado_cliente_administrador_id: Optional[int] = Field(
        None,
        description="Se role=Contador: ID do usuário (Cliente Administrador) cujos clientes este contador pode ver",
    )

    @field_validator("cpf")
    @classmethod
    def validar_cpf(cls, v: Optional[str]) -> Optional[str]:
        if not v or not str(v).strip():
            return None
        valido, formatado, erro = CPFValidator.validar_e_formatar(v)
        if not valido:
            raise ValueError(erro or "CPF inválido")
        return formatado

class UsuarioResponse(UsuarioBase):
    """Schema para resposta de usuário (inclui cpf, rg, documento_path para edição no frontend)."""
    id: int
    role_id: Optional[int] = None
    role: Optional[RoleResponse] = None
    contador_vinculado_cliente_administrador_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    # Redefinir para garantir que entrem na serialização da resposta (editar usuário)
    cpf: Optional[str] = Field(None, max_length=14, description="CPF do usuário")
    rg: Optional[str] = Field(None, max_length=20, description="RG do usuário")
    documento_path: Optional[str] = Field(None, max_length=500, description="Caminho do documento/anexo")
    # Apenas para Super Administrador: vínculo do usuário (Técnico/Subcliente) com Cliente Administrador
    vinculo_cliente_administrador_id: Optional[int] = Field(
        None,
        description="Se role Técnico ou Subcliente: ID do Cliente Administrador ao qual está vinculado (preenchido só para Super Administrador)",
    )
    vinculo_cliente_administrador_nome: Optional[str] = Field(
        None,
        description="Se role Técnico ou Subcliente: nome do Cliente Administrador (preenchido só para Super Administrador)",
    )

    model_config = ConfigDict(from_attributes=True)

class UsuarioListResponse(BaseModel):
    """Schema para resposta de lista de usuários"""
    usuarios: List[UsuarioResponse]
    total: int
    skip: int
    limit: int 