# PDV Ibix - Schemas Marketplace
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

# Vitrine — página pública /{slug}: hero (H1 + parágrafo) usa nome_fantasia + descrição longa
VITRINE_HERO_NOME_FANTASIA_MAX = 80
VITRINE_HERO_DESCRICAO_LONGA_MAX = 1200


# --- Categorias plataforma ---
class CategoriaPlataformaBase(BaseModel):
    nome: str
    slug: Optional[str] = None
    descricao: Optional[str] = None
    icone: Optional[str] = None
    ordem: Optional[int] = None
    ativa: bool = True
    categoria_pai_id: Optional[int] = None


class CategoriaPlataformaCreate(CategoriaPlataformaBase):
    pass


class CategoriaPlataformaUpdate(BaseModel):
    nome: Optional[str] = None
    slug: Optional[str] = None
    descricao: Optional[str] = None
    icone: Optional[str] = None
    ordem: Optional[int] = None
    ativa: Optional[bool] = None
    categoria_pai_id: Optional[int] = None


class CategoriaPlataformaResponse(BaseModel):
    id: int
    nome: str
    slug: Optional[str] = None
    descricao: Optional[str] = None
    icone: Optional[str] = None
    ordem: Optional[int] = None
    ativa: bool = True  # default para linhas antigas ou NULL no DB
    categoria_pai_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Loja marketplace ---
class LojaMarketplaceBase(BaseModel):
    status: str = "pendente"
    slug: Optional[str] = Field(
        None,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9\- ]*[A-Za-z0-9]$|^[A-Za-z0-9]$",
        description="Slug público da loja (será normalizado no backend).",
    )
    nome_loja: Optional[str] = Field(None, max_length=200)
    nome_fantasia: Optional[str] = Field(None, max_length=VITRINE_HERO_NOME_FANTASIA_MAX)
    categoria_principal: Optional[str] = None
    subcategoria: Optional[str] = None
    cidade_seo: Optional[str] = None
    estado_seo: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    og_image_url: Optional[str] = None
    seo_enabled: bool = True
    descricao: Optional[str] = Field(None, max_length=VITRINE_HERO_DESCRICAO_LONGA_MAX)
    descricao_curta: Optional[str] = Field(None, max_length=320)
    descricao_longa: Optional[str] = Field(None, max_length=VITRINE_HERO_DESCRICAO_LONGA_MAX)
    vitrine_hero_titulo_uma_linha: bool = False
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    tipo_entrega: str = "retirada"
    raio_entrega_km: Optional[int] = None
    taxa_entrega_fixa: Optional[Decimal] = None
    entrega_gratis_apos: Optional[Decimal] = None


class LojaMarketplaceCreate(LojaMarketplaceBase):
    cliente_id: int


class LojaMarketplaceUpdate(BaseModel):
    status: Optional[str] = None
    slug: Optional[str] = Field(
        None,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9\- ]*[A-Za-z0-9]$|^[A-Za-z0-9]$",
        description="Slug público da loja (será normalizado no backend).",
    )
    nome_loja: Optional[str] = Field(None, max_length=200)
    nome_fantasia: Optional[str] = Field(None, max_length=VITRINE_HERO_NOME_FANTASIA_MAX)
    categoria_principal: Optional[str] = None
    subcategoria: Optional[str] = None
    cidade_seo: Optional[str] = None
    estado_seo: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    og_image_url: Optional[str] = None
    seo_enabled: Optional[bool] = None
    descricao: Optional[str] = Field(None, max_length=VITRINE_HERO_DESCRICAO_LONGA_MAX)
    descricao_curta: Optional[str] = Field(None, max_length=320)
    descricao_longa: Optional[str] = Field(None, max_length=VITRINE_HERO_DESCRICAO_LONGA_MAX)
    vitrine_hero_titulo_uma_linha: Optional[bool] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    logo_blob: Optional[str] = Field(None, description="Imagem logo em base64 (data URL); ao enviar, salva arquivo e preenche logo_url")
    banner_blob: Optional[str] = Field(None, description="Imagem banner em base64 (data URL); ao enviar, salva arquivo e preenche banner_url")
    tipo_entrega: Optional[str] = None
    raio_entrega_km: Optional[int] = None
    taxa_entrega_fixa: Optional[Decimal] = None
    entrega_gratis_apos: Optional[Decimal] = None
    formato_frete: Optional[str] = None


class LojaMarketplaceResponse(BaseModel):
    id: int
    cliente_id: int
    status: str
    slug: Optional[str] = None
    nome_loja: Optional[str] = None
    nome_fantasia: Optional[str] = None
    categoria_principal: Optional[str] = None
    subcategoria: Optional[str] = None
    cidade_seo: Optional[str] = None
    estado_seo: Optional[str] = None
    slug_categoria_cidade: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    og_image_url: Optional[str] = None
    seo_enabled: bool = True
    descricao: Optional[str] = None
    descricao_curta: Optional[str] = None
    descricao_longa: Optional[str] = None
    vitrine_hero_titulo_uma_linha: bool = False
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    tipo_entrega: str
    raio_entrega_km: Optional[int] = None
    taxa_entrega_fixa: Optional[Decimal] = None
    entrega_gratis_apos: Optional[Decimal] = None
    formato_frete: str = "sem_frete"
    avaliacao_media: Optional[Decimal] = None
    total_vendas_marketplace: int = 0
    faturamento_total: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Preenchidos só em GET /marketplace/loja?cliente_id= (a partir do cadastro do estabelecimento)
    sugestao_nome_loja: Optional[str] = None
    sugestao_nome_fantasia: Optional[str] = None
    sugestao_cidade_seo: Optional[str] = None
    sugestao_estado_seo: Optional[str] = None

    model_config = {"from_attributes": True}


class LojaFretePublicResponse(BaseModel):
    formato_frete: str
    tipo_entrega: str
    taxa_entrega_fixa: Optional[Decimal] = None
    entrega_gratis_apos: Optional[Decimal] = None
    raio_entrega_km: Optional[int] = None


# --- Anúncio plataforma ---
class AnuncioPlataformaBase(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    imagens: Optional[str] = None  # JSON string
    preco_original: Decimal
    preco_promocional: Optional[Decimal] = None
    tipo_estoque: str = "sincronizado"
    estoque_minimo_alerta: Optional[int] = 5
    categoria_id: Optional[int] = None
    atributos: Optional[str] = None  # JSON: [{"nome":"Marca","valor":"X"}, ...] - características do produto (marketplaces)
    frete_sobrescrever_loja: bool = False
    formato_frete_produto: Optional[str] = None
    taxa_entrega_fixa_produto: Optional[Decimal] = None
    entrega_gratis_apos_produto: Optional[Decimal] = None
    og_image_url: Optional[str] = Field(None, max_length=500, description="URL absoluta (CDN) imagem OG 1.91:1; opcional")


class AnuncioPlataformaCreate(AnuncioPlataformaBase):
    loja_id: int
    produto_ca_id: int


class AnuncioPlataformaUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    imagens: Optional[str] = None
    preco_original: Optional[Decimal] = None
    preco_promocional: Optional[Decimal] = None
    tipo_estoque: Optional[str] = None
    estoque_minimo_alerta: Optional[int] = None
    categoria_id: Optional[int] = None
    status: Optional[str] = None
    atributos: Optional[str] = None
    og_image_url: Optional[str] = Field(None, max_length=500, description="URL absoluta (CDN) imagem OG 1.91:1")
    frete_sobrescrever_loja: Optional[bool] = None
    formato_frete_produto: Optional[str] = None
    taxa_entrega_fixa_produto: Optional[Decimal] = None
    entrega_gratis_apos_produto: Optional[Decimal] = None


class AnuncioPlataformaResponse(BaseModel):
    id: int
    loja_id: int
    produto_ca_id: int
    categoria_id: Optional[int] = None
    status: str
    titulo: str
    descricao: Optional[str] = None
    imagens: Optional[str] = None
    preco_original: Decimal
    preco_promocional: Optional[Decimal] = None
    tipo_estoque: str
    estoque_atual: Optional[Decimal] = None
    estoque_minimo_alerta: Optional[int] = None
    visualizacoes: int = 0
    cliques: int = 0
    vendas: int = 0
    ultima_sincronizacao: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    atributos: Optional[str] = None
    frete_sobrescrever_loja: bool = False
    formato_frete_produto: Optional[str] = None
    taxa_entrega_fixa_produto: Optional[Decimal] = None
    entrega_gratis_apos_produto: Optional[Decimal] = None
    og_image_url: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Consumidor (vitrine) ---
class ConsumidorCadastro(BaseModel):
    email: str
    senha: str
    nome: str
    telefone: Optional[str] = None
    documento: Optional[str] = None
    aceite_termos: bool = False
    loja_id: Optional[int] = None  # contexto vitrine: define tenant_id = loja.cliente_id


class ConsumidorLogin(BaseModel):
    email: str
    senha: str
    loja_id: Optional[int] = None  # contexto vitrine: busca por tenant_id + email


class ConsumidorUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    documento: Optional[str] = None
    aceite_marketing: Optional[bool] = None


class ConsumidorResponse(BaseModel):
    id: int
    email: str
    nome: str
    telefone: Optional[str] = None
    documento: Optional[str] = None
    ativo: bool
    aceite_marketing: bool = False
    email_verificado: bool = False
    origem_social_provider: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConsumidorSocialLogin(BaseModel):
    provider: str = Field(..., description="google | facebook | apple")
    access_token: Optional[str] = None
    id_token: Optional[str] = None
    aceite_termos: bool = True
    nome_fallback: Optional[str] = None


class ConsumidorSocialLoginResponse(BaseModel):
    status: str = Field(..., description="authenticated | pending_link")
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    consumidor: Optional[ConsumidorResponse] = None
    link_token: Optional[str] = None
    message: Optional[str] = None
    requires_password: Optional[bool] = Field(
        default=None,
        description="pending_link: se a conta tem senha local (confirmação por senha). False = só token OAuth.",
    )


class ConsumidorSocialConfirmLink(BaseModel):
    link_token: str
    senha: Optional[str] = None


class EnderecoConsumidorCreate(BaseModel):
    apelido: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    tipo_endereco: Optional[str] = "principal"
    referencia: Optional[str] = None
    principal: bool = False


class EnderecoConsumidorResponse(BaseModel):
    id: int
    consumidor_id: int
    apelido: Optional[str] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    tipo_endereco: str = "principal"
    referencia: Optional[str] = None
    principal: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Checkout (criar pedido) ---
class CheckoutItem(BaseModel):
    anuncio_id: int
    quantidade: int = Field(..., ge=1)


class PedidoCheckoutCreate(BaseModel):
    loja_id: int
    itens: List[CheckoutItem] = Field(..., min_length=1)
    comprador_nome: str
    comprador_email: str
    comprador_telefone: Optional[str] = None
    comprador_documento: Optional[str] = None
    destinatario_nome: Optional[str] = Field(None, max_length=200, description="Nome do destinatário quando diferente do comprador")
    endereco_entrega: Optional[str] = None
    endereco_cep: Optional[str] = None
    endereco_logradouro: Optional[str] = None
    endereco_numero: Optional[str] = None
    endereco_complemento: Optional[str] = None
    endereco_bairro: Optional[str] = None
    endereco_cidade: Optional[str] = None
    endereco_uf: Optional[str] = None
    tipo_entrega: str = "retirada"
    desconto: Decimal = Decimal("0")
    taxa_entrega: Decimal = Decimal("0")
    aceite_marketing: bool = False
    aceite_politica_privacidade: bool = Field(
        False,
        description="Obrigatório True para finalizar o pedido (aceite da Política de Privacidade).",
    )
    canal_origem: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    observacoes_cliente: Optional[str] = None
    payment_method: str = Field(
        "pix",
        description="Forma de pagamento no gateway: pix, credit_card ou boleto (conforme suporte do provedor).",
    )
    idempotency_key: Optional[str] = Field(None, max_length=128, description="Chave para evitar duplo pedido (retorna pedido existente em 24h)")


class MarketplacePixCheckoutPayload(BaseModel):
    """PIX inline (Checkout Transparente / app mobile)."""

    copia_cola: str
    qr_code: str = ""
    qr_code_base64: Optional[str] = None
    expiracao_minutos: int = 30


class PedidoCheckoutResponse(BaseModel):
    id: int
    numero_pedido: str
    loja_id: int
    status_pedido: str
    status_pagamento: str
    status_entrega: str = "pendente"
    subtotal: Optional[Decimal] = None
    desconto: Optional[Decimal] = None
    taxa_entrega: Optional[Decimal] = None
    total: Decimal
    comprador_email: Optional[str] = None
    created_at: Optional[datetime] = None
    redirect_url: Optional[str] = None
    transaction_uuid: Optional[str] = None
    checkout_type: Optional[str] = None
    qr_code: Optional[str] = None
    copy_paste_code: Optional[str] = None
    pix: Optional[MarketplacePixCheckoutPayload] = None

    model_config = {"from_attributes": True}


class CheckoutItemUnificado(BaseModel):
    anuncio_id: int
    quantidade: int = Field(..., ge=1)
    loja_id: int


class PedidoCheckoutUnificadoCreate(BaseModel):
    """Checkout com itens de várias lojas; um pagamento (modo plataforma em todas as lojas)."""

    itens: List[CheckoutItemUnificado] = Field(..., min_length=1)
    comprador_nome: str
    comprador_email: str
    comprador_telefone: Optional[str] = None
    comprador_documento: Optional[str] = None
    destinatario_nome: Optional[str] = Field(None, max_length=200)
    endereco_entrega: Optional[str] = None
    endereco_cep: Optional[str] = None
    endereco_logradouro: Optional[str] = None
    endereco_numero: Optional[str] = None
    endereco_complemento: Optional[str] = None
    endereco_bairro: Optional[str] = None
    endereco_cidade: Optional[str] = None
    endereco_uf: Optional[str] = None
    tipo_entrega: str = "retirada"
    desconto: Decimal = Decimal("0")
    taxa_entrega: Decimal = Decimal("0")
    aceite_marketing: bool = False
    aceite_politica_privacidade: bool = Field(False)
    canal_origem: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    observacoes_cliente: Optional[str] = None
    payment_method: str = Field(
        "pix",
        description="Forma de pagamento no gateway: pix, credit_card ou boleto (conforme suporte do provedor).",
    )
    idempotency_key: Optional[str] = Field(None, max_length=128)


class PedidoResumoUnificado(BaseModel):
    id: int
    numero_pedido: str
    loja_id: int
    total: Decimal


class PedidoCheckoutUnificadoResponse(BaseModel):
    session_uuid: str
    pedidos: List[PedidoResumoUnificado]
    comprador_email: Optional[str] = None
    redirect_url: Optional[str] = None
    transaction_uuid: Optional[str] = None
    checkout_type: Optional[str] = None
    qr_code: Optional[str] = None
    copy_paste_code: Optional[str] = None
    pix: Optional[MarketplacePixCheckoutPayload] = None


# --- Pedido (gestão loja - resposta completa) ---
class PedidoItemGestaoResponse(BaseModel):
    id: int
    anuncio_id: int
    nome_produto_snapshot: str = ""
    quantidade: int
    preco_unitario: Decimal
    preco_total: Decimal

    model_config = {"from_attributes": True}


class PedidoMarketplaceResponse(BaseModel):
    id: int
    numero_pedido: str
    loja_id: int
    comprador_id: Optional[int] = None
    comprador_nome: str
    comprador_email: Optional[str] = None
    comprador_telefone: Optional[str] = None
    destinatario_nome: Optional[str] = None
    subtotal: Decimal
    desconto: Decimal
    taxa_entrega: Decimal
    total: Decimal
    status_pedido: str
    status_pagamento: str
    status_entrega: str = "pendente"
    endereco_entrega: Optional[str] = None
    tipo_entrega: str
    created_at: Optional[datetime] = None
    itens: List[PedidoItemGestaoResponse] = []

    model_config = {"from_attributes": True}


class PedidoMarketplaceUpdate(BaseModel):
    status_pedido: Optional[str] = None
    status_pagamento: Optional[str] = None


# --- Status pedido marketplace (configurável Super Admin) ---
class StatusPedidoMarketplaceResponse(BaseModel):
    id: int
    codigo: str
    label: str
    ordem: int = 0
    ativo: bool = True

    model_config = {"from_attributes": True}


class StatusPedidoMarketplaceCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=30)
    label: str = Field(..., min_length=1, max_length=100)
    ordem: int = 0
    ativo: bool = True


class StatusPedidoMarketplaceUpdate(BaseModel):
    label: Optional[str] = Field(None, min_length=1, max_length=100)
    ordem: Optional[int] = None
    ativo: Optional[bool] = None


# --- Extrato loja ---
class ExtratoLojaResponse(BaseModel):
    id: int
    loja_id: int
    pedido_id: Optional[int] = None
    tipo: str
    descricao: Optional[str] = None
    valor_bruto: Optional[Decimal] = None
    valor_taxa: Optional[Decimal] = None
    valor_liquido: Optional[Decimal] = None
    saldo_anterior: Optional[Decimal] = None
    saldo_atual: Optional[Decimal] = None
    status: str
    data_disponivel: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Avaliação (vitrine) ---
class AvaliacaoCreate(BaseModel):
    nota: int = Field(..., ge=1, le=5)
    comentario: Optional[str] = None


class AvaliacaoResponse(BaseModel):
    id: int
    pedido_id: int
    anuncio_id: int
    loja_id: int
    comprador_nome: Optional[str] = None
    nota: int
    comentario: Optional[str] = None
    resposta_loja: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Completar cadastro (GUEST → REGISTERED) ---
class CompletarCadastroBody(BaseModel):
    email: str
    numero_pedido: str
    senha: str


# --- Consulta pública de pedido ---
class PedidoStatusEventoOut(BaseModel):
    """Evento da timeline do pedido (para exibição em /loja/acompanhar-pedido)."""
    tipo_evento: str
    status_codigo: Optional[str] = None
    status_label: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PedidoConsultarResponse(BaseModel):
    id: Optional[int] = None
    numero_pedido: str
    status_pedido: str
    status_pagamento: str
    status_entrega: str
    total: Decimal
    created_at: Optional[datetime] = None
    itens: List[dict] = []
    timeline: List[dict] = []  # eventos ordenados por created_at (linha do tempo para o comprador)

    model_config = {"from_attributes": True}


# --- Áreas de Entrega (abrangência por cidade) ---
class LojaAreaEntregaCreate(BaseModel):
    cidade: str = Field(..., max_length=100)
    uf: str = Field(..., max_length=2)
    codigo_ibge: Optional[int] = None
    taxa_entrega: Decimal = Decimal("0")
    prazo_dias: Optional[int] = None


class LojaAreaEntregaUpdate(BaseModel):
    cidade: Optional[str] = None
    uf: Optional[str] = None
    codigo_ibge: Optional[int] = None
    taxa_entrega: Optional[Decimal] = None
    prazo_dias: Optional[int] = None
    ativo: Optional[bool] = None


class LojaAreaEntregaResponse(BaseModel):
    id: int
    loja_id: int
    cidade: str
    uf: str
    codigo_ibge: Optional[int] = None
    taxa_entrega: Decimal
    prazo_dias: Optional[int] = None
    ativo: bool

    model_config = {"from_attributes": True}


# --- Vitrine pública (anúncio resumido para listagem) ---
class AnuncioVitrineResponse(BaseModel):
    id: int
    titulo: str
    loja_id: Optional[int] = None
    preco_original: Decimal
    preco_promocional: Optional[Decimal] = None
    imagens: Optional[List[str]] = None
    og_image_url: Optional[str] = None
    slug_loja: Optional[str] = None
    nome_loja: Optional[str] = None
    estoque_atual: Optional[Decimal] = None
    status: str
    frete_formato_efetivo: Optional[str] = None
    frete_origem_regra: Optional[str] = None
    frete_gratis: bool = False
    distancia_km: Optional[float] = None
    cidade_loja: Optional[str] = None
    uf_loja: Optional[str] = None
    bairro_loja: Optional[str] = None
    distancia_rota_km: Optional[float] = None
    duracao_rota_min: Optional[float] = None
    rota_estimada: Optional[bool] = None

    model_config = {"from_attributes": True}


# --- Reparacao retroativa de comprador_id em pedidos (Super Admin) ---
class ReparacaoCompradorRequest(BaseModel):
    """Entrada do endpoint de reparacao de comprador em pedidos antigos."""
    tenant_id: int = Field(..., gt=0, description="ID do tenant (clientes.id) a reparar.")
    email: Optional[str] = Field(
        None,
        description="Filtrar a reparacao a um e-mail especifico (case-insensitive). Sem filtro = todos os pares do tenant.",
    )
    dry_run: bool = Field(
        True,
        description="True = relatorio sem alterar dados (default). False = aplica e grava audit_log.",
    )


class ReparacaoCompradorPar(BaseModel):
    """Par (registered, guest) candidato a reatribuicao de comprador_id."""
    registered_id: int
    guest_id: int
    email: str
    pedidos_afetados: List[int]
    aplicado: bool
    motivo_skip: Optional[str] = None  # dry_run | multiple_registered | no_orders


class ReparacaoCompradorResultado(BaseModel):
    """Relatorio da reparacao por tenant."""
    tenant_id: int
    dry_run: bool
    total_candidatos: int
    total_aplicados: int
    total_conflitos: int
    pares: List[ReparacaoCompradorPar] = []
