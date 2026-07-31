# PDV Ibix — Perfil do lojista (CA) para Superadmin
from typing import List, Optional

from pydantic import BaseModel, Field


class CategoriaVitrineItem(BaseModel):
    id: int
    nome: str
    codigo: Optional[str] = None
    icone: Optional[str] = None
    descricao: Optional[str] = None


class ClienteLojistaEmpresaBlock(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    cpf: Optional[str] = None
    cep: Optional[str] = None
    endereco: str
    cidade: str
    uf: str
    contato: str
    telefone: str
    email: str
    banco_nome: Optional[str] = None
    banco_codigo: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None
    tipo_conta: Optional[str] = None
    pix_chave: Optional[str] = None
    created_at: Optional[str] = None


class ClienteLojistaEmpresaFiscalBlock(BaseModel):
    id: int
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    cnpj: Optional[str] = None
    ambiente: Optional[str] = None
    ativo: Optional[bool] = None


class ClienteLojistaResponsavelBlock(BaseModel):
    usuario_id: Optional[int] = None
    nome: Optional[str] = None
    email: Optional[str] = None
    ativo: Optional[bool] = None
    role: Optional[str] = None
    tenant_id: Optional[int] = None


class ClienteLojistaTenantBlock(BaseModel):
    id: Optional[int] = None
    nome: Optional[str] = None
    slug: Optional[str] = None


class ClienteLojistaLojaBlock(BaseModel):
    id: Optional[int] = None
    nome_loja: Optional[str] = None
    nome_fantasia: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[str] = None


class ClientePerfilLojistaResponse(BaseModel):
    cliente_id: int
    empresa: ClienteLojistaEmpresaBlock
    empresa_fiscal: ClienteLojistaEmpresaFiscalBlock
    responsavel_ca: ClienteLojistaResponsavelBlock
    tenant: ClienteLojistaTenantBlock
    loja_marketplace: Optional[ClienteLojistaLojaBlock] = None
    categorias_vitrine: List[CategoriaVitrineItem] = Field(default_factory=list)
