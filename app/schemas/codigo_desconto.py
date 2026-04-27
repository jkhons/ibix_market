# PDV Ibix - Schemas de código de desconto e divulgador (Fase 2)
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DivulgadorCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    cpf_cnpj: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    usuario_id: Optional[int] = None


class DivulgadorUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    cpf_cnpj: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    ativo: Optional[bool] = None
    usuario_id: Optional[int] = None


class DivulgadorResponse(BaseModel):
    id: int
    nome: str
    cpf_cnpj: Optional[str] = None
    email: Optional[str] = None
    ativo: bool
    usuario_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DivulgadorRegraCreate(BaseModel):
    percentual_plano_ativo: int = Field(ge=0, le=100, default=0)
    recebe_primeira_parcela: bool = False
    percentual_comissao: int = Field(ge=0, le=100, default=25)


class DivulgadorRegraUpdate(BaseModel):
    percentual_plano_ativo: Optional[int] = Field(None, ge=0, le=100)
    recebe_primeira_parcela: Optional[bool] = None
    percentual_comissao: Optional[int] = Field(None, ge=0, le=100)


class DivulgadorRegraResponse(BaseModel):
    id: int
    divulgador_id: int
    percentual_plano_ativo: int
    recebe_primeira_parcela: bool
    percentual_comissao: int
    created_at: datetime

    class Config:
        from_attributes = True


class CodigoDescontoCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=50)
    tipo_promocao: str = Field(min_length=1, max_length=50)
    desconto_primeira_parcela_percent: int = Field(ge=0, le=100, default=0)
    desconto_mensalidade_percent: int = Field(ge=0, le=100, default=0)
    meses_desconto: Optional[int] = Field(None, ge=1)
    divulgador_id: Optional[int] = Field(None, description="ID do divulgador (se já existir).")
    representante_usuario_id: Optional[int] = Field(None, description="ID do usuário Representante (Administrador). Se informado, o sistema usa ou cria um divulgador vinculado a ele. Obrigatório se divulgador_id não for informado.")


class CodigoDescontoUpdate(BaseModel):
    tipo_promocao: Optional[str] = Field(None, max_length=50)
    desconto_primeira_parcela_percent: Optional[int] = Field(None, ge=0, le=100)
    desconto_mensalidade_percent: Optional[int] = Field(None, ge=0, le=100)
    meses_desconto: Optional[int] = Field(None, ge=1)
    ativo: Optional[bool] = None
    divulgador_id: Optional[int] = None
    representante_usuario_id: Optional[int] = Field(None, description="ID do Representante (Administrador). Se informado, usa ou cria divulgador vinculado a ele.")


class CodigoDescontoResponse(BaseModel):
    id: int
    codigo: str
    tipo_promocao: str
    desconto_primeira_parcela_percent: int
    desconto_mensalidade_percent: int
    meses_desconto: Optional[int] = None
    ativo: bool
    divulgador_id: Optional[int] = None
    representante_nome: Optional[str] = Field(None, description="Nome do Representante (Administrador) vinculado ao divulgador do código")
    created_at: datetime

    class Config:
        from_attributes = True
