# PDV Ibix - Schemas Fornecedor por Estabelecimento (Fase 2)
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from ..utils.cnpj_validator import CNPJValidator


def _normalizar_cnpj(v: Optional[str]) -> Optional[str]:
    """Normaliza CNPJ para dígitos-only (14 chars) ou None. Alinhado com nfe_entrada_service._cnpj_limpo."""
    if not v or not v.strip():
        return None
    limpo = CNPJValidator.limpar_cnpj(v)
    if not limpo:
        return None
    valido, erro = CNPJValidator.validar_cnpj(v)
    if not valido:
        raise ValueError(erro or "CNPJ inválido")
    return limpo


class FornecedorClienteBase(BaseModel):
    cliente_id: int
    nome: str
    cnpj: Optional[str] = None
    contato: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    ativo: bool = True

    @field_validator("cnpj", mode="before")
    @classmethod
    def validar_cnpj(cls, v: Optional[str]) -> Optional[str]:
        return _normalizar_cnpj(v)


class FornecedorClienteCreate(FornecedorClienteBase):
    pass


class FornecedorClienteUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    contato: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    ativo: Optional[bool] = None

    @field_validator("cnpj", mode="before")
    @classmethod
    def validar_cnpj(cls, v: Optional[str]) -> Optional[str]:
        return _normalizar_cnpj(v)


class FornecedorClienteResponse(FornecedorClienteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
