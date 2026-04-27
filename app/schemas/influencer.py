# PDV Ibix - Schemas do modulo de Influencers
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

# ── Influencer (Divulgador) ────────────────────────────────────────────

class InfluencerCadastroPublico(BaseModel):
    """Cadastro publico do influencer — linguagem simples."""
    nome: str = Field(min_length=2, max_length=255, description="Seu nome completo")
    email: EmailStr = Field(description="Seu melhor e-mail")
    password: str = Field(min_length=6, description="Crie uma senha")
    confirm_password: str = Field(description="Confirme a senha")
    telefone: Optional[str] = Field(None, max_length=20, description="WhatsApp com DDD")
    cidade: Optional[str] = Field(None, max_length=150, description="Sua cidade")
    estado: Optional[str] = Field(None, max_length=2, description="UF")
    nicho: Optional[str] = Field(None, max_length=100, description="Qual sua area? (ex: Automotivo, Moda, Tecnologia)")
    redes_sociais: Optional[str] = Field(
        None,
        description='JSON: {"facebook":"...", "instagram":"@...", "tiktok":"@...", "youtube":"..."}',
    )
    tipo_atuacao: Optional[str] = Field(None, max_length=50, description="Como quer divulgar: propaganda, cupom, live, todos")
    bio: Optional[str] = Field(None, max_length=2000, description="Fale um pouco sobre voce")


class InfluencerResponse(BaseModel):
    id: int
    nome: str
    email: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    ativo: bool
    tipo: Optional[str] = None
    status: Optional[str] = None
    nicho: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    redes_sociais: Optional[str] = None
    engajamento: Optional[int] = None
    score_performance: Optional[int] = None
    tipo_atuacao: Optional[str] = None
    bio: Optional[str] = None
    telefone: Optional[str] = None
    foto_url: Optional[str] = None
    usuario_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InfluencerUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    cpf_cnpj: Optional[str] = Field(None, max_length=20)
    telefone: Optional[str] = Field(None, max_length=20)
    cidade: Optional[str] = Field(None, max_length=150)
    estado: Optional[str] = Field(None, max_length=2)
    nicho: Optional[str] = Field(None, max_length=100)
    redes_sociais: Optional[str] = None
    engajamento: Optional[int] = None
    tipo_atuacao: Optional[str] = Field(None, max_length=50)
    bio: Optional[str] = Field(None, max_length=2000)
    foto_url: Optional[str] = Field(None, max_length=500)
    ativo: Optional[bool] = None


class InfluencerStatusUpdate(BaseModel):
    status: str = Field(description="pendente, teste, aprovado, parceiro, bloqueado")
    motivo: Optional[str] = Field(None, max_length=500, description="Motivo da alteracao")


# ── Campanha ────────────────────────────────────────────────────────────

class CampanhaCreate(BaseModel):
    divulgador_id: int
    loja_id: Optional[int] = None
    titulo: str = Field(min_length=1, max_length=255)
    descricao: Optional[str] = None
    tipo: str = Field(description="propaganda, cupom, live")
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    valor_fixo: Optional[Decimal] = None
    percentual_comissao: Optional[int] = Field(None, ge=0, le=100)
    modelo_pagamento: Optional[str] = Field(None, description="fixo, comissao, hibrido")
    codigo_desconto_id: Optional[int] = Field(None, description="Vincular cupom existente (ou deixar vazio para auto-gerar)")
    is_teste: bool = False


class CampanhaUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=255)
    descricao: Optional[str] = None
    status: Optional[str] = Field(None, description="rascunho, ativa, pausada, finalizada, cancelada")
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    valor_fixo: Optional[Decimal] = None
    percentual_comissao: Optional[int] = Field(None, ge=0, le=100)
    modelo_pagamento: Optional[str] = None


class CampanhaResponse(BaseModel):
    id: int
    divulgador_id: int
    loja_id: Optional[int] = None
    titulo: str
    descricao: Optional[str] = None
    tipo: str
    status: str
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    valor_fixo: Optional[Decimal] = None
    percentual_comissao: Optional[int] = None
    modelo_pagamento: Optional[str] = None
    codigo_desconto_id: Optional[int] = None
    is_teste: bool
    created_at: datetime
    influencer_nome: Optional[str] = None
    cupom_codigo: Optional[str] = None

    class Config:
        from_attributes = True


# ── Link ────────────────────────────────────────────────────────────────

class LinkCreate(BaseModel):
    campanha_id: Optional[int] = None
    divulgador_id: int
    url_destino: str = Field(min_length=1, max_length=1000)


class LinkResponse(BaseModel):
    id: int
    campanha_id: Optional[int] = None
    divulgador_id: int
    url_destino: str
    codigo_rastreio: str
    url_rastreavel: Optional[str] = None
    ativo: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Metrica ─────────────────────────────────────────────────────────────

class MetricaResponse(BaseModel):
    id: int
    campanha_id: Optional[int] = None
    divulgador_id: int
    cliques: int = 0
    visualizacoes: int = 0
    vendas: int = 0
    faturamento: Decimal = Decimal("0")
    conversoes_cupom: int = 0
    periodo_inicio: Optional[date] = None
    periodo_fim: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MetricaAgregada(BaseModel):
    total_cliques: int = 0
    total_vendas: int = 0
    total_faturamento: Decimal = Decimal("0")
    total_conversoes_cupom: int = 0
    total_campanhas: int = 0
