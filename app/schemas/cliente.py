# PDV Ibix - Cliente Schemas
import re
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator

from ..utils.cnpj_validator import CNPJValidator
from ..utils.cpf_validator import CPFValidator


def _validar_cnpj_valor(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    valido, cnpj_formatado, erro = CNPJValidator.validar_e_formatar(v)
    if not valido:
        raise ValueError(erro)
    return cnpj_formatado


def _validar_cpf_valor(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    valido, cpf_formatado, erro = CPFValidator.validar_e_formatar(v)
    if not valido:
        raise ValueError(erro)
    return cpf_formatado


def _validar_telefone_valor(v):
    telefone_limpo = re.sub(r'[^0-9]', '', v)
    if len(telefone_limpo) < 10 or len(telefone_limpo) > 11:
        raise ValueError('Telefone deve ter 10 ou 11 dígitos')
    if len(telefone_limpo) == 11:
        return f"({telefone_limpo[:2]}) {telefone_limpo[2:7]}-{telefone_limpo[7:]}"
    return f"({telefone_limpo[:2]}) {telefone_limpo[2:6]}-{telefone_limpo[6:]}"


def _validar_uf_valor(v):
    ufs_validas = [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
        'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
        'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    ]
    if v.upper() not in ufs_validas:
        raise ValueError('UF inválida')
    return v.upper()


def _validar_cep_valor(v):
    if v is None or v == '':
        return v
    cep_limpo = re.sub(r'[^0-9]', '', v)
    if len(cep_limpo) != 8:
        raise ValueError('CEP deve ter 8 dígitos')
    return f"{cep_limpo[:5]}-{cep_limpo[5:]}"


class ClienteBase(BaseModel):
    """Schema base para cliente. PJ = CNPJ; PF = CPF (aptos a receber notas fiscais)."""
    nome: str
    cnpj: Optional[str] = None
    cpf: Optional[str] = None
    cep: Optional[str] = None
    endereco: str
    cidade: str
    uf: str
    contato: str
    telefone: str
    email: EmailStr

class ClienteCreate(ClienteBase):
    """Schema para criação de cliente. Exatamente um de cnpj ou cpf deve ser informado."""

    @model_validator(mode='before')
    @classmethod
    def cnpj_ou_cpf_obrigatorio(cls, data):
        if isinstance(data, dict):
            cnpj = (data.get('cnpj') or '').strip() if data.get('cnpj') is not None else ''
            cpf = (data.get('cpf') or '').strip() if data.get('cpf') is not None else ''
            if not cnpj and not cpf:
                raise ValueError('Informe CNPJ (Pessoa Jurídica) ou CPF (Pessoa Física)')
            if cnpj and cpf:
                raise ValueError('Informe apenas CNPJ ou apenas CPF, não ambos')
        return data

    @field_validator('cnpj')
    @classmethod
    def validar_cnpj(cls, v):
        return _validar_cnpj_valor(v)

    @field_validator('cpf')
    @classmethod
    def validar_cpf(cls, v):
        return _validar_cpf_valor(v)
    
    @field_validator('telefone')
    @classmethod
    def validar_telefone(cls, v):
        return _validar_telefone_valor(v)
    
    @field_validator('uf')
    @classmethod
    def validar_uf(cls, v):
        return _validar_uf_valor(v)
    
    @field_validator('cep')
    @classmethod
    def validar_cep(cls, v):
        return _validar_cep_valor(v)

class ClienteUpdate(BaseModel):
    """Schema para atualização de cliente"""
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    cpf: Optional[str] = None
    cep: Optional[str] = None
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    contato: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    
    @field_validator('cnpj')
    @classmethod
    def validar_cnpj(cls, v):
        if v is None:
            return v
        return _validar_cnpj_valor(v)

    @field_validator('cpf')
    @classmethod
    def validar_cpf(cls, v):
        if v is None:
            return v
        return _validar_cpf_valor(v)

    @field_validator('telefone')
    @classmethod
    def validar_telefone(cls, v):
        if v is None:
            return v
        return _validar_telefone_valor(v)

    @field_validator('uf')
    @classmethod
    def validar_uf(cls, v):
        if v is None:
            return v
        return _validar_uf_valor(v)

    @field_validator('cep')
    @classmethod
    def validar_cep(cls, v):
        if v is None:
            return v
        return _validar_cep_valor(v)

class ClienteResponse(ClienteBase):
    """Schema para resposta de cliente"""
    id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True

class ClienteListResponse(BaseModel):
    """Schema para listagem de clientes"""
    clientes: List[ClienteResponse]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int

class ClienteSearchParams(BaseModel):
    """Schema para parâmetros de busca"""
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    cpf: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    pagina: int = 1
    por_pagina: int = 10
    cliente_ids: Optional[List[int]] = None  # Saas.md Fase 3: filtrar por escopo (Administrador/Cliente Admin)
    empresa_fiscal: Optional[str] = None  # "true"=só Empresa Fiscal, "false"=só Subcliente, None=todos (apenas Admin/SuperAdmin)
