# PDV Ibix - Schemas Pydantic v2 para API mobile
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


# ─── Push Token ──────────────────────────────────────────────
class PushTokenCreate(BaseModel):
    token: str = Field(..., min_length=10, max_length=512)
    plataforma: str = Field(..., pattern="^(ios|android)$")
    device_id: Optional[str] = Field(None, max_length=255)

class PushTokenResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    token: str
    plataforma: str
    ativo: bool


# ─── Refresh Token / Auth ────────────────────────────────────
class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20)

class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class AppleSignInRequest(BaseModel):
    id_token: str = Field(..., min_length=10)
    authorization_code: Optional[str] = None
    nome: Optional[str] = None


# ─── Favoritos ───────────────────────────────────────────────
class FavoritoAnuncioResumo(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    titulo: str
    preco_original: float
    preco_promocional: Optional[float] = None
    imagem_capa: Optional[str] = None
    status: str

class FavoritoResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    anuncio_id: int
    created_at: datetime
    anuncio: Optional[FavoritoAnuncioResumo] = None

class FavoritosListResponse(BaseModel):
    items: List[FavoritoResponse]
    total: int


# ─── Notificações ────────────────────────────────────────────
class NotificacaoResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    tipo: str
    titulo: str
    mensagem: str
    dados_json: Optional[Any] = None
    lida: bool
    created_at: datetime

class NotificacoesListResponse(BaseModel):
    items: List[NotificacaoResponse]
    total: int
    nao_lidas: int

class NotificacaoMarcarLidaRequest(BaseModel):
    ids: Optional[List[int]] = Field(None, description="IDs específicos; se vazio marca todas", max_length=500)


# ─── App Versão ──────────────────────────────────────────────
class AppVersionResponse(BaseModel):
    model_config = {"from_attributes": True}
    plataforma: str
    versao_minima: str
    versao_recomendada: str
    url_loja: Optional[str] = None
    mensagem: Optional[str] = None

class AppVersionUpdateRequest(BaseModel):
    versao_minima: Optional[str] = Field(None, pattern=r"^\d+\.\d+\.\d+$")
    versao_recomendada: Optional[str] = Field(None, pattern=r"^\d+\.\d+\.\d+$")
    url_loja: Optional[str] = Field(None, max_length=500)
    mensagem: Optional[str] = None


# ─── Cupons ──────────────────────────────────────────────────
class CupomValidarRequest(BaseModel):
    codigo: str = Field(..., min_length=3, max_length=50)
    valor_total: Decimal
    loja_id: Optional[int] = None

class CupomValidarResponse(BaseModel):
    valido: bool
    desconto: Optional[Decimal] = None
    tipo_desconto: Optional[str] = None
    mensagem: str
    code: Optional[str] = None

class CupomDisponivelResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    codigo: str
    tipo_desconto: str
    valor_desconto: Decimal
    valor_minimo_pedido: Optional[Decimal] = None
    valido_ate: Optional[datetime] = None
    loja_nome: Optional[str] = None

class CupomAdminCreate(BaseModel):
    codigo: str = Field(..., min_length=3, max_length=50)
    tipo_desconto: Literal["percentual", "fixo"]
    valor_desconto: Decimal = Field(..., gt=0)
    valor_minimo_pedido: Optional[Decimal] = None
    uso_maximo: Optional[int] = Field(None, ge=1)
    uso_maximo_por_consumidor: Optional[int] = Field(1, ge=1)
    valido_de: Optional[datetime] = None
    valido_ate: Optional[datetime] = None
    loja_id: Optional[int] = None

class CupomAdminUpdate(BaseModel):
    valor_desconto: Optional[Decimal] = Field(None, gt=0)
    valor_minimo_pedido: Optional[Decimal] = None
    uso_maximo: Optional[int] = Field(None, ge=1)
    uso_maximo_por_consumidor: Optional[int] = Field(None, ge=1)
    valido_de: Optional[datetime] = None
    valido_ate: Optional[datetime] = None
    ativo: Optional[bool] = None

class CupomAdminResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    codigo: str
    tipo_desconto: str
    valor_desconto: Decimal
    valor_minimo_pedido: Optional[Decimal] = None
    uso_maximo: Optional[int] = None
    uso_atual: int
    uso_maximo_por_consumidor: Optional[int] = None
    valido_de: Optional[datetime] = None
    valido_ate: Optional[datetime] = None
    ativo: bool
    loja_id: Optional[int] = None
    created_at: datetime


# ─── Cancelamento / Devolução ────────────────────────────────
class CancelarPedidoRequest(BaseModel):
    motivo_id: int
    descricao_adicional: Optional[str] = Field(None, max_length=500)

class DevolucaoCreateRequest(BaseModel):
    motivo_id: int
    tipo: Literal["devolucao", "reembolso"]
    descricao: Optional[str] = Field(None, min_length=20, max_length=2000)
    fotos: Optional[List[str]] = Field(None, max_length=5)

class DevolucaoResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    status: str
    tipo: str
    motivo_descricao: Optional[str] = None
    descricao: Optional[str] = None
    fotos_json: Optional[Any] = None
    valor_reembolso: Optional[Decimal] = None
    resposta_loja: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class DevolucaoAdminUpdate(BaseModel):
    status: Literal["em_analise", "aprovada", "recusada", "finalizada"]
    resposta: Optional[str] = Field(None, max_length=2000)
    valor_reembolso: Optional[Decimal] = Field(None, ge=0)

class MotivoResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    descricao: str
    tipo: str
    ordem: int

class MotivoAdminCreate(BaseModel):
    descricao: str = Field(..., min_length=3, max_length=255)
    tipo: Literal["cancelamento", "devolucao"]
    ordem: int = 0

class MotivoAdminUpdate(BaseModel):
    descricao: Optional[str] = Field(None, min_length=3, max_length=255)
    ativo: Optional[bool] = None
    ordem: Optional[int] = None


# ─── Parcelamento ────────────────────────────────────────────
class ParcelaItem(BaseModel):
    parcelas: int
    valor_parcela: Decimal
    total: Decimal
    juros: bool
    taxa_juros: Optional[Decimal] = None

class ParcelamentoResponse(BaseModel):
    valor_original: Decimal
    opcoes: List[ParcelaItem]


# ─── Chat ────────────────────────────────────────────────────
class ConversaIniciarRequest(BaseModel):
    loja_id: int
    anuncio_id: Optional[int] = None
    mensagem: str = Field(..., min_length=1, max_length=2000)

class MensagemEnviarRequest(BaseModel):
    texto: Optional[str] = Field(None, max_length=2000)
    imagem_url: Optional[str] = Field(None, max_length=500)

    def model_post_init(self, __context: Any) -> None:
        if not self.texto and not self.imagem_url:
            raise ValueError("Envie texto ou imagem")

class MensagemResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    conversa_id: int
    remetente_tipo: str
    remetente_id: int
    texto: Optional[str] = None
    imagem_url: Optional[str] = None
    lida: bool
    created_at: datetime

class ConversaResumo(BaseModel):
    id: int
    loja_id: int
    loja_nome: Optional[str] = None
    anuncio_id: Optional[int] = None
    status: str
    ultima_mensagem_em: Optional[datetime] = None
    ultima_mensagem_texto: Optional[str] = None
    nao_lidas: int = 0
    created_at: datetime

class ConversasListResponse(BaseModel):
    items: List[ConversaResumo]
    total: int


# ─── LGPD ────────────────────────────────────────────────────
class ConsentimentoItem(BaseModel):
    tipo: Literal["marketing", "analytics", "terceiros"]
    aceito: bool

class ConsentimentosResponse(BaseModel):
    items: List[ConsentimentoItem]

class ConsentimentoUpdateRequest(BaseModel):
    consentimentos: List[ConsentimentoItem]

class ExcluirContaRequest(BaseModel):
    senha: str = Field(..., min_length=1)


# ─── Busca ───────────────────────────────────────────────────
class AutocompleteResponse(BaseModel):
    termos: List[str]

class TermoPopularResponse(BaseModel):
    termo: str
    contagem: int


# ─── Error padronizado ───────────────────────────────────────
class ErrorResponse(BaseModel):
    detail: str
    code: str
