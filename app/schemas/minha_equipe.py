# PDV Ibix - Schemas Minha equipe (Saas.md Fase 6.2)
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SubClienteUsuarioCreate(BaseModel):
    """Cria usuário (role Subcliente) e vincula ao cliente via AreaCliente."""
    nome: str = Field(..., min_length=2)
    email: EmailStr
    senha: str = Field(..., min_length=6)


class VincularTecnicoRequest(BaseModel):
    """Vincular técnico à equipe por email ou ID.
    Se o usuário não existir, cria automaticamente um usuário com role Técnico.
    Para criar novo técnico: email obrigatório; nome e senha obrigatórios."""
    email: Optional[EmailStr] = None
    usuario_id: Optional[int] = None
    nome: Optional[str] = Field(None, min_length=2)
    senha: Optional[str] = Field(None, min_length=6)
