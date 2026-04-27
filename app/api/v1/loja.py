# PDV Ibix - API Vitrine (loja pública + consumidor)
"""APIs públicas da vitrine e áreas do consumidor (minha-conta, meus-pedidos)."""
import base64
import hashlib
import json
import math
import os
import secrets
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.auth import (
    AuthConfig,
    create_consumidor_refresh_token,
    create_consumidor_token,
    rotate_consumidor_refresh_token,
)
from ...core.config import settings
from ...core.error_codes import (
    APP_VERSAO_NAO_ENCONTRADA,
    AUTH_APPLE_VERIFICATION_FAILED,
    PUSH_TOKEN_NAO_ENCONTRADO,
)
from ...core.rate_limiter import (
    check_forgot_password_rate_limit,
    check_geo_rate_limit,
    check_loja_cadastro_rate_limit,
    check_loja_checkout_rate_limit,
    check_loja_login_rate_limit,
    check_loja_nova_tentativa_rate_limit,
    check_loja_pedido_consultar_rate_limit,
    check_reset_password_rate_limit,
)
from ...core.redis_cache import get_loja_categorias_cached
from ...core.slug_utils import SLUG_REGEX, normalize_slug_or_400
from ...database.connection import get_db
from ...models import (
    AnuncioPlataforma,
    AvaliacaoMarketplace,
    Cliente,
    ConsumidorMarketplace,
    ConsumidorSocialIdentity,
    ConsumidorSocialLinkPending,
    Empresa,
    EnderecoConsumidor,
    ExtratoLoja,
    LojaAreaEntrega,
    LojaMarketplace,
    MarketplaceCheckoutSession,
    MarketplaceCheckoutSessionPedido,
    MaterialCategoria,
    PaymentTransaction,
    PedidoItemMarketplace,
    PedidoMarketplace,
    ProdutoCliente,
)
from ...schemas.marketplace import (
    AnuncioVitrineResponse,
    AvaliacaoCreate,
    AvaliacaoResponse,
    CategoriaPlataformaResponse,
    CheckoutItem,
    CompletarCadastroBody,
    ConsumidorCadastro,
    ConsumidorLogin,
    ConsumidorResponse,
    ConsumidorSocialConfirmLink,
    ConsumidorSocialLogin,
    ConsumidorSocialLoginResponse,
    ConsumidorUpdate,
    EnderecoConsumidorCreate,
    EnderecoConsumidorResponse,
    MarketplacePixCheckoutPayload,
    PedidoCheckoutCreate,
    PedidoCheckoutResponse,
    PedidoCheckoutUnificadoCreate,
    PedidoCheckoutUnificadoResponse,
    PedidoConsultarResponse,
    PedidoResumoUnificado,
)
from ...schemas.mobile import (
    AppleSignInRequest,
    AppVersionResponse,
    PushTokenCreate,
    PushTokenResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
)
from ...services.apple_auth_service import verify_apple_id_token
from ...services.marketplace_guest_service import emit_integration_event
from ...services.password_reset_service import (
    request_reset_loja,
    reset_password_loja,
    validate_token_loja,
)
from ...services.push_token_service import registrar_push_token, remover_push_token

router = APIRouter(prefix="/loja", tags=["Loja (vitrine)"])


def _public_base_url_for_checkout(request: Request) -> str:
    """Base pública para back_urls e webhooks dos gateways (Mercado Pago, PagBank, etc.).
    Ordem alinhada ao SEO: SEO_PUBLIC_BASE_URL → host da requisição → APP_URL.
    Evita notification_url / retorno com http interno ou host do container."""
    explicit = (getattr(settings, "SEO_PUBLIC_BASE_URL", None) or "").strip().rstrip("/")
    if explicit:
        return explicit
    base = str(request.base_url).rstrip("/") if request.base_url else ""
    if base:
        return base
    app_u = (getattr(settings, "APP_URL", None) or "").strip().rstrip("/")
    return app_u or ""


def _marketplace_pix_from_stored_response(pr: Optional[dict]) -> Optional[MarketplacePixCheckoutPayload]:
    """Reidrata objeto pix a partir de payment_transactions.provider_response (idempotência)."""
    if not pr or not isinstance(pr, dict):
        return None
    from ...services.payments.mercadopago_api import minutes_until_mp_expiration

    ct = (pr.get("checkout_type") or "").strip().lower()
    copia = (pr.get("copy_paste_code") or pr.get("qr_code") or "").strip()
    if ct != "pix" or not copia:
        return None
    return MarketplacePixCheckoutPayload(
        copia_cola=copia,
        qr_code=(pr.get("qr_code") or copia),
        qr_code_base64=pr.get("qr_code_base64"),
        expiracao_minutos=minutes_until_mp_expiration(pr.get("expires_at")),
    )


def _lojas_modo_plataforma_obrigatorio_unificado(db: Session, loja_ids: List[int]) -> None:
    for lid in loja_ids:
        loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == lid, LojaMarketplace.status == "ativo").first()
        if not loja:
            raise HTTPException(status_code=404, detail=f"Loja {lid} não encontrada ou inativa")
        emp = (
            db.query(Empresa)
            .filter(Empresa.cliente_id == loja.cliente_id, Empresa.ativo.is_(True))
            .first()
        )
        if not emp or (emp.modo_recebimento or "").strip().lower() != "plataforma":
            raise HTTPException(
                status_code=400,
                detail="Checkout unificado exige modo de recebimento plataforma em todas as lojas participantes.",
            )


def _pedido_body_from_unificado(
    u: PedidoCheckoutUnificadoCreate, loja_id: int, itens: List[CheckoutItem]
) -> PedidoCheckoutCreate:
    return PedidoCheckoutCreate(
        loja_id=loja_id,
        itens=itens,
        comprador_nome=u.comprador_nome,
        comprador_email=u.comprador_email,
        comprador_telefone=u.comprador_telefone,
        comprador_documento=u.comprador_documento,
        destinatario_nome=u.destinatario_nome,
        endereco_entrega=u.endereco_entrega,
        endereco_cep=u.endereco_cep,
        endereco_logradouro=u.endereco_logradouro,
        endereco_numero=u.endereco_numero,
        endereco_complemento=u.endereco_complemento,
        endereco_bairro=u.endereco_bairro,
        endereco_cidade=u.endereco_cidade,
        endereco_uf=u.endereco_uf,
        tipo_entrega=u.tipo_entrega,
        desconto=u.desconto,
        taxa_entrega=u.taxa_entrega,
        aceite_marketing=u.aceite_marketing,
        aceite_politica_privacidade=u.aceite_politica_privacidade,
        canal_origem=u.canal_origem,
        utm_source=u.utm_source,
        utm_medium=u.utm_medium,
        utm_campaign=u.utm_campaign,
        observacoes_cliente=u.observacoes_cliente,
        payment_method=u.payment_method,
        idempotency_key=None,
    )


def _normalize_loja_slug(raw_slug: Optional[str]) -> Optional[str]:
    if raw_slug is None:
        return None
    slug = str(raw_slug).strip()
    if not slug:
        return None
    slug = normalize_slug_or_400(slug, field_name="Slug de loja", max_len=100)
    if not SLUG_REGEX.match(slug):
        raise HTTPException(status_code=400, detail="Slug de loja inválido")
    return slug


def _debug_log_vitrine(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    # region agent log
    try:
        payload = {
            "sessionId": "925a90",
            "runId": "post-fix-backend-probe",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open("/central_solumatica/pdv_solumatica/.cursor/debug-925a90.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except Exception:
        pass
    # endregion


COOKIE_LOJA_CONSUMIDOR = "loja_consumidor_token"

_CANAL_ATR_VITRINE_SHARE = "share_cliente"


def _merge_checkout_unificado_attribution(request: Request, body: PedidoCheckoutUnificadoCreate) -> PedidoCheckoutUnificadoCreate:
    """Preenche UTMs/canal a partir do cookie ibix_vitrine_share (Fase 02) se o body não trouxe utm_source."""
    from ...core.loja_attribution import vitrine_share_cookie_present

    if not getattr(settings, "VITRINE_UTM_ATTRIBUTION_ENABLED", True):
        return body
    if (body.utm_source or "").strip():
        return body
    if not vitrine_share_cookie_present(request):
        return body
    return body.model_copy(
        update={
            "canal_origem": _CANAL_ATR_VITRINE_SHARE,
            "utm_source": "compartilhamento",
            "utm_medium": "cliente",
            "utm_campaign": "vitrine_social",
        }
    )


def _merge_checkout_single_attribution(request: Request, body: PedidoCheckoutCreate) -> PedidoCheckoutCreate:
    from ...core.loja_attribution import vitrine_share_cookie_present

    if not getattr(settings, "VITRINE_UTM_ATTRIBUTION_ENABLED", True):
        return body
    if (body.utm_source or "").strip():
        return body
    if not vitrine_share_cookie_present(request):
        return body
    return body.model_copy(
        update={
            "canal_origem": _CANAL_ATR_VITRINE_SHARE,
            "utm_source": "compartilhamento",
            "utm_medium": "cliente",
            "utm_campaign": "vitrine_social",
        }
    )


@router.get("/auth/social/config")
async def loja_auth_social_config():
    """Retorna client IDs OAuth da vitrine (públicos). Sem secrets."""
    def _trim(v: Optional[str]) -> Optional[str]:
        if not v or not str(v).strip():
            return None
        return str(v).strip()

    return {
        "google_client_id": _trim(settings.LOJA_OAUTH_GOOGLE_CLIENT_ID),
        "facebook_app_id": _trim(settings.LOJA_OAUTH_FACEBOOK_APP_ID),
        "apple_client_id": _trim(settings.LOJA_OAUTH_APPLE_CLIENT_ID),
    }


def _token_from_request(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:].strip()
    return request.cookies.get(COOKIE_LOJA_CONSUMIDOR)


async def get_current_consumidor(
    request: Request,
    db: Session = Depends(get_db),
):
    """Dependency: retorna ConsumidorMarketplace a partir do cookie loja_consumidor_token ou Bearer."""
    token = _token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = AuthConfig.verify_token(token)
    except HTTPException:
        raise
    if payload.get("tipo") != "consumidor":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido para consumidor")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    try:
        cid = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.id == cid).first()
    if not consumidor or not consumidor.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Consumidor não encontrado ou inativo")
    return consumidor


async def get_current_consumidor_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[ConsumidorMarketplace]:
    """Retorna consumidor se autenticado; senão None (checkout como visitante)."""
    token = _token_from_request(request)
    if not token:
        return None
    try:
        payload = AuthConfig.verify_token(token)
    except HTTPException:
        return None
    if payload.get("tipo") != "consumidor":
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        cid = int(sub)
    except (TypeError, ValueError):
        return None
    consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.id == cid).first()
    if not consumidor or not consumidor.ativo:
        return None
    return consumidor


# --- Público: categorias ---
@router.get("/categorias", response_model=List[CategoriaPlataformaResponse])
async def listar_categorias_vitrine(
    response: Response,
    ativa: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Lista categorias da vitrine baseadas em categorias de estoque com produtos publicados."""
    response.headers["Cache-Control"] = "public, max-age=60"

    def fetch():
        # Exibe todas as categorias de estoque ativas na vitrine.
        # O filtro de produtos é aplicado ao clicar na categoria.
        rows = (
            db.query(
                MaterialCategoria.id.label("id"),
                MaterialCategoria.nome.label("nome"),
                MaterialCategoria.descricao.label("descricao"),
                MaterialCategoria.icone.label("icone"),
            )
            .filter(MaterialCategoria.ativo == ativa)
            .order_by(MaterialCategoria.nome)
            .all()
        )
        data = []
        for r in rows:
            data.append(
                {
                    "id": r.id,
                    "nome": r.nome,
                    "slug": None,
                    "descricao": r.descricao,
                    "icone": r.icone,
                    "ordem": None,
                    "ativa": bool(ativa),
                    "categoria_pai_id": None,
                    "created_at": None,
                }
            )
        return data

    data = get_loja_categorias_cached(str(ativa), fetch)
    return [CategoriaPlataformaResponse.model_validate(d) for d in data]


def _normalize_image_url(url: str) -> str:
    """Retorna URL pronta para o front: paths relativos viram /static/... (padrão marketplaces)."""
    if not url or not isinstance(url, str):
        return ""
    u = url.strip()
    if u.startswith("http://") or u.startswith("https://") or u.startswith("/"):
        return u
    return "/static/" + u if u else ""


def _imagens_as_list(imagens) -> List[str]:
    """Normaliza imagens (JSON string ou lista) para lista de URLs para a vitrine. Paths viram /static/..."""
    if imagens is None:
        return []
    raw: List[str] = []
    if isinstance(imagens, list):
        raw = [str(u) for u in imagens if u]
    else:
        try:
            parsed = json.loads(imagens) if isinstance(imagens, str) else imagens
            raw = [str(u) for u in (parsed if isinstance(parsed, list) else []) if u]
        except Exception:
            raw = []
    return [_normalize_image_url(u) for u in raw if u]


def _imagens_anuncio_ou_fallback(anuncio: AnuncioPlataforma, db: Session) -> List[str]:
    """Retorna lista de URLs de imagens do anúncio; se vazia, monta a partir do produto (foto_peca + midias tipo imagem)."""
    imgs = _imagens_as_list(anuncio.imagens)
    if imgs:
        return imgs
    prod = db.query(ProdutoCliente).filter(ProdutoCliente.id == anuncio.produto_ca_id).first()
    if not prod:
        return []
    from .marketplace import _galeria_produto_para_imagens
    galeria_json = _galeria_produto_para_imagens(prod)
    return _imagens_as_list(galeria_json) if galeria_json else []


# --- Público: geolocalização ---

@router.get("/geo/cidades")
async def listar_cidades_lojas_ativas(
    q: Optional[str] = Query(None, max_length=100, description="Filtro parcial por cidade"),
    db: Session = Depends(get_db),
):
    """Lista cidades (únicas) com pelo menos uma loja ativa, incluindo coordenadas médias para proximidade."""
    from sqlalchemy import func as sqlfunc
    base = (
        db.query(
            sqlfunc.trim(Cliente.cidade).label("cidade"),
            sqlfunc.upper(sqlfunc.trim(Cliente.uf)).label("uf"),
            sqlfunc.avg(Cliente.latitude).label("lat"),
            sqlfunc.avg(Cliente.longitude).label("lng"),
        )
        .join(LojaMarketplace, LojaMarketplace.cliente_id == Cliente.id)
        .filter(LojaMarketplace.status == "ativo", Cliente.cidade.isnot(None))
    )
    if q and q.strip():
        base = base.filter(Cliente.cidade.ilike(f"%{q.strip()}%"))
    rows = (
        base.group_by(sqlfunc.trim(Cliente.cidade), sqlfunc.upper(sqlfunc.trim(Cliente.uf)))
        .order_by(sqlfunc.trim(Cliente.cidade))
        .all()
    )
    return [
        {
            "cidade": r.cidade,
            "uf": r.uf,
            "lat": round(r.lat, 6) if r.lat else None,
            "lng": round(r.lng, 6) if r.lng else None,
        }
        for r in rows
    ]


@router.get("/geo/cidade-proxima", dependencies=[Depends(check_geo_rate_limit)])
async def cidade_mais_proxima(
    lat: float = Query(..., ge=-34, le=6, description="Latitude do usuário"),
    lng: float = Query(..., ge=-74, le=-28, description="Longitude do usuário"),
    db: Session = Depends(get_db),
):
    """Encontra a cidade com loja ativa mais próxima das coordenadas do usuário.
    Usa Haversine no banco para performance."""
    from app.services.geo_service import haversine_km

    lojas = (
        db.query(
            Cliente.cidade,
            Cliente.uf,
            Cliente.latitude,
            Cliente.longitude,
        )
        .join(LojaMarketplace, LojaMarketplace.cliente_id == Cliente.id)
        .filter(
            LojaMarketplace.status == "ativo",
            Cliente.latitude.isnot(None),
            Cliente.longitude.isnot(None),
        )
        .all()
    )
    if not lojas:
        return {"cidade": None, "uf": None, "distancia_km": None}

    melhor = None
    for loja in lojas:
        dist = haversine_km(lat, lng, loja.latitude, loja.longitude)
        if melhor is None or dist < melhor[1]:
            melhor = (loja, dist)

    return {
        "cidade": melhor[0].cidade.strip() if melhor[0].cidade else None,
        "uf": melhor[0].uf.strip().upper() if melhor[0].uf else None,
        "distancia_km": round(melhor[1], 1),
        "lat": round(melhor[0].latitude, 6),
        "lng": round(melhor[0].longitude, 6),
    }


@router.get("/geo/reverso", dependencies=[Depends(check_geo_rate_limit)])
async def geo_reverso(
    lat: float = Query(..., ge=-34, le=6),
    lng: float = Query(..., ge=-74, le=-28),
):
    """Converte lat/lng em cidade/UF via Nominatim (server-side)."""
    import httpx as _httpx
    try:
        with _httpx.Client(timeout=10.0) as client:
            r = client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": str(lat), "lon": str(lng), "format": "json", "zoom": "10"},
                headers={"User-Agent": "PDV-Ibix/1.0 (geo-reverso)"},
            )
            r.raise_for_status()
            data = r.json()
        addr = data.get("address", {})
        cidade = addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("village")
        uf = addr.get("state")
        return {"cidade": cidade, "uf": uf}
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao consultar serviço de geolocalização")


@router.get("/geo/geocodificar", dependencies=[Depends(check_geo_rate_limit)])
async def geo_geocodificar(
    cep: str = Query(..., min_length=8, max_length=10, description="CEP (00000-000 ou 00000000)"),
    numero: Optional[str] = Query(None, max_length=20, description="Número do imóvel"),
    complemento: Optional[str] = Query(None, max_length=80, description="Complemento (apto, bloco)"),
    cidade: Optional[str] = Query(None, max_length=100, description="Cidade (opcional, ajuda fallback)"),
    uf: Optional[str] = Query(None, max_length=2, description="UF (opcional, ajuda fallback)"),
):
    """Geocodifica endereço residencial (CEP + número) com a melhor precisão disponível.

    Retorna lat/lng e cidade/UF normalizados. O campo `precision` indica se o resultado
    é rooftop/range/locality (o front pode rejeitar `locality` quando a UX exigir
    proximidade certeira).
    """
    from ...services.geo_service import PRECISION_LOCALITY, geocode_address

    if not (numero or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Informe o número do imóvel para geocodificação certeira.",
        )

    result = geocode_address(cep=cep, numero=numero, complemento=complemento, cidade=cidade, uf=uf)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Endereço não encontrado. Confira CEP e número e tente novamente.",
        )
    if result.precision == PRECISION_LOCALITY:
        raise HTTPException(
            status_code=422,
            detail="Endereço retornou apenas a cidade (sem rua). Confira o número informado.",
        )
    return {
        "lat": result.lat,
        "lng": result.lng,
        "cidade": result.cidade,
        "uf": result.uf,
        "bairro": result.bairro,
        "endereco_formatado": result.endereco_formatado,
        "precision": result.precision,
        "provider": result.provider,
    }


# --- Público: anúncios publicados ---
@router.get("/anuncios", response_model=dict)
async def listar_anuncios_vitrine(
    request: Request,
    response: Response,
    categoria_id: Optional[int] = Query(None),
    categoria_ids: Optional[List[int]] = Query(
        None,
        description="Uma ou mais categorias de estoque do produto; filtra por qualquer uma. Se informado, prevalece sobre categoria_id.",
    ),
    cliente_ids: Optional[List[int]] = Query(
        None,
        description="Uma ou mais lojas por tenant (clientes.id / CA). Filtra anúncios publicados dessas lojas.",
    ),
    loja_slug: Optional[str] = Query(None, description="Slug da loja"),
    q: Optional[str] = Query(
        None,
        description="Busca por palavras (título, descrição, atributos, nome/código do produto, categoria). "
        "Várias palavras: todas devem aparecer em algum desses campos (ex.: «mouse usb» encontra «MOUSE BRIGHT USB»).",
    ),
    sort: Optional[str] = Query(
        "recent",
        description="Ordenação: recent, preco_asc, preco_desc, nome, random, proximidade",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=100),
    somente_promocao: Optional[bool] = Query(
        None,
        description="Se true, apenas anúncios com preço promocional preenchido e > 0 (campo de oferta no anúncio).",
    ),
    lat: Optional[float] = Query(None, ge=-34, le=6, description="Latitude do usuário (para proximidade)"),
    lng: Optional[float] = Query(None, ge=-74, le=-28, description="Longitude do usuário (para proximidade)"),
    geo_cidade: Optional[str] = Query(None, max_length=100, description="Cidade do usuário (priorização por mesma cidade)"),
    geo_uf: Optional[str] = Query(None, max_length=2, description="UF do usuário (priorização por mesmo estado)"),
    db: Session = Depends(get_db),
):
    """Lista anúncios publicados de lojas ativas. Filtros: categoria(s), loja (slug), busca textual.
    Suporta geolocalização: lat/lng para distância, geo_cidade/geo_uf para priorização regional.
    sort=proximidade ordena por distância (requer lat+lng)."""
    from sqlalchemy import and_, case, func

    from app.services.geo_service import haversine_km

    # region agent log
    _debug_log_vitrine(
        "B1",
        "app/api/v1/loja.py:listar_anuncios_vitrine:entry",
        "Entrada endpoint anuncios",
        {
            "categoria_id": categoria_id,
            "categoria_ids": categoria_ids,
            "cliente_ids": cliente_ids,
            "loja_slug": loja_slug,
            "somente_promocao": somente_promocao,
            "q_len": len(q.strip()) if q else 0,
            "sort": sort,
            "skip": skip,
            "limit": limit,
            "lat": lat,
            "lng": lng,
            "geo_cidade": geo_cidade,
            "geo_uf": geo_uf,
            "rid": request.query_params.get("_dbg_rid"),
        },
    )
    # endregion

    has_geo = lat is not None and lng is not None
    if sort == "proximidade" and not has_geo:
        sort = "recent"

    response.headers["Cache-Control"] = "public, max-age=60"
    try:
        query = (
            db.query(AnuncioPlataforma)
            .join(LojaMarketplace)
            .filter(
                AnuncioPlataforma.status == "publicado",
                LojaMarketplace.status == "ativo",
            )
        )

        joined_cliente = False
        if has_geo or geo_cidade or geo_uf:
            query = query.join(Cliente, Cliente.id == LojaMarketplace.cliente_id)
            joined_cliente = True

        joined_produto = False
        ids_filtro: Optional[List[int]] = None
        if categoria_ids:
            ids_filtro = [int(x) for x in categoria_ids if x is not None][:200]
            if not ids_filtro:
                ids_filtro = None
        if ids_filtro:
            query = query.join(ProdutoCliente, ProdutoCliente.id == AnuncioPlataforma.produto_ca_id)
            joined_produto = True
            query = query.filter(ProdutoCliente.categoria_id.in_(ids_filtro))
        elif categoria_id is not None:
            query = query.join(ProdutoCliente, ProdutoCliente.id == AnuncioPlataforma.produto_ca_id)
            joined_produto = True
            query = query.filter(ProdutoCliente.categoria_id == categoria_id)
        if loja_slug:
            loja_slug_norm = _normalize_loja_slug(loja_slug)
            query = query.filter(func.lower(LojaMarketplace.slug) == loja_slug_norm)
        if cliente_ids:
            cids_loja = [int(x) for x in cliente_ids if x is not None][:200]
            if cids_loja:
                query = query.filter(LojaMarketplace.cliente_id.in_(cids_loja))
        if somente_promocao is True:
            query = query.filter(
                AnuncioPlataforma.preco_promocional.isnot(None),
                AnuncioPlataforma.preco_promocional > 0,
            )
        if q and q.strip():
            if not joined_produto:
                query = query.join(ProdutoCliente, ProdutoCliente.id == AnuncioPlataforma.produto_ca_id)
                joined_produto = True
            query = query.outerjoin(MaterialCategoria, MaterialCategoria.id == ProdutoCliente.categoria_id)
            tokens = [t for t in q.strip().split() if t][:12]
            for tok in tokens:
                term = f"%{tok}%"
                query = query.filter(
                    (AnuncioPlataforma.titulo.ilike(term))
                    | (AnuncioPlataforma.descricao.ilike(term))
                    | (AnuncioPlataforma.atributos.ilike(term))
                    | (ProdutoCliente.nome.ilike(term))
                    | (ProdutoCliente.descricao.ilike(term))
                    | (ProdutoCliente.codigo.ilike(term))
                    | (MaterialCategoria.nome.ilike(term))
                    | (MaterialCategoria.descricao.ilike(term))
                )

        preco_efetivo = case(
            (
                and_(
                    AnuncioPlataforma.preco_promocional.isnot(None),
                    AnuncioPlataforma.preco_promocional > 0,
                ),
                AnuncioPlataforma.preco_promocional,
            ),
            else_=AnuncioPlataforma.preco_original,
        )

        if sort == "proximidade" and has_geo:
            dist_expr = (
                6371 * func.acos(
                    func.least(1.0, func.greatest(-1.0,
                        func.cos(func.radians(lat)) * func.cos(func.radians(Cliente.latitude))
                        * func.cos(func.radians(Cliente.longitude) - func.radians(lng))
                        + func.sin(func.radians(lat)) * func.sin(func.radians(Cliente.latitude))
                    ))
                )
            )
            query = query.order_by(
                case((Cliente.latitude.is_(None), 999999), else_=dist_expr).asc(),
                AnuncioPlataforma.id,
            )
        elif sort == "preco_asc":
            query = query.order_by(preco_efetivo.asc(), AnuncioPlataforma.id)
        elif sort == "preco_desc":
            query = query.order_by(preco_efetivo.desc(), AnuncioPlataforma.id)
        elif sort == "nome":
            query = query.order_by(AnuncioPlataforma.titulo.asc(), AnuncioPlataforma.id)
        elif sort == "random":
            query = query.order_by(func.random())
        else:
            if joined_cliente and (geo_cidade or geo_uf):
                whens = []
                if geo_cidade and geo_uf:
                    whens.append((
                        and_(
                            func.lower(func.trim(Cliente.cidade)) == geo_cidade.strip().lower(),
                            func.upper(func.trim(Cliente.uf)) == geo_uf.strip().upper(),
                        ),
                        0,
                    ))
                if geo_uf:
                    whens.append((
                        func.upper(func.trim(Cliente.uf)) == geo_uf.strip().upper(),
                        1,
                    ))
                geo_priority = case(*whens, else_=2)
                query = query.order_by(geo_priority.asc(), AnuncioPlataforma.updated_at.desc(), AnuncioPlataforma.id)
            else:
                query = query.order_by(AnuncioPlataforma.updated_at.desc(), AnuncioPlataforma.id)

        total = query.count()
        rows = query.offset(skip).limit(limit).all()
        # region agent log
        _debug_log_vitrine(
            "B2",
            "app/api/v1/loja.py:listar_anuncios_vitrine:dbResult",
            "Consulta anuncios concluida",
            {"total": total, "rows_len": len(rows), "skip": skip, "limit": limit, "rid": request.query_params.get("_dbg_rid")},
        )
        # endregion

        _cliente_cache: Dict[int, Optional[Cliente]] = {}

        def _get_cliente(cliente_id: int) -> Optional[Cliente]:
            if cliente_id not in _cliente_cache:
                _cliente_cache[cliente_id] = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            return _cliente_cache[cliente_id]

        items = []
        for r in rows:
            imgs = _imagens_anuncio_ou_fallback(r, db)
            dist_km = None
            cidade_loja = None
            uf_loja = None
            if r.loja and r.loja.cliente_id:
                cli = _get_cliente(r.loja.cliente_id)
                if cli:
                    cidade_loja = cli.cidade
                    uf_loja = cli.uf
                    if has_geo and cli.latitude is not None and cli.longitude is not None:
                        dist_km = round(haversine_km(lat, lng, cli.latitude, cli.longitude), 1)

            estoque_lista = r.estoque_atual
            if (getattr(r, "tipo_estoque", None) or "").strip().lower() == "sincronizado":
                pc_an = getattr(r, "produto_cliente", None)
                if pc_an is not None and getattr(pc_an, "quantidade_atual", None) is not None:
                    estoque_lista = float(pc_an.quantidade_atual)
            items.append(
                AnuncioVitrineResponse(
                    id=r.id,
                    titulo=r.titulo,
                    loja_id=r.loja_id,
                    preco_original=r.preco_original,
                    preco_promocional=r.preco_promocional,
                    imagens=imgs,
                    og_image_url=(getattr(r, "og_image_url", None) or "").strip() or None,
                    slug_loja=r.loja.slug if r.loja else None,
                    nome_loja=r.loja.nome_loja if r.loja else None,
                    estoque_atual=estoque_lista,
                    status=r.status,
                    frete_formato_efetivo=(
                        (r.formato_frete_produto if r.frete_sobrescrever_loja else (r.loja.formato_frete if r.loja else None))
                        or "sem_frete"
                    ),
                    frete_origem_regra="produto" if r.frete_sobrescrever_loja else "loja",
                    frete_gratis=(
                        ((r.formato_frete_produto if r.frete_sobrescrever_loja else (r.loja.formato_frete if r.loja else None)) == "gratis")
                    ),
                    distancia_km=dist_km,
                    cidade_loja=cidade_loja,
                    uf_loja=uf_loja,
                )
            )
        return {"items": items, "total": total, "skip": skip, "limit": limit}
    except Exception as e:
        # region agent log
        _debug_log_vitrine(
            "B3",
            "app/api/v1/loja.py:listar_anuncios_vitrine:exception",
            "Falha no endpoint anuncios",
            {"error": str(e), "error_type": type(e).__name__, "skip": skip, "limit": limit, "rid": request.query_params.get("_dbg_rid")},
        )
        # endregion
        raise


def _montar_anuncio_response(
    anuncio: AnuncioPlataforma,
    cli: Optional[Cliente],
    db: Session,
    *,
    distancia_rota_km: Optional[float] = None,
    duracao_rota_min: Optional[float] = None,
    rota_estimada: Optional[bool] = None,
    distancia_haversine_km: Optional[float] = None,
) -> AnuncioVitrineResponse:
    """Monta AnuncioVitrineResponse com dados de loja/produto/distancia. Reusa em multiplos endpoints."""
    imgs = _imagens_anuncio_ou_fallback(anuncio, db)
    estoque_lista = anuncio.estoque_atual
    if (getattr(anuncio, "tipo_estoque", None) or "").strip().lower() == "sincronizado":
        pc_an = getattr(anuncio, "produto_cliente", None)
        if pc_an is not None and getattr(pc_an, "quantidade_atual", None) is not None:
            estoque_lista = float(pc_an.quantidade_atual)
    return AnuncioVitrineResponse(
        id=anuncio.id,
        titulo=anuncio.titulo,
        loja_id=anuncio.loja_id,
        preco_original=anuncio.preco_original,
        preco_promocional=anuncio.preco_promocional,
        imagens=imgs,
        og_image_url=(getattr(anuncio, "og_image_url", None) or "").strip() or None,
        slug_loja=anuncio.loja.slug if anuncio.loja else None,
        nome_loja=anuncio.loja.nome_loja if anuncio.loja else None,
        estoque_atual=estoque_lista,
        status=anuncio.status,
        frete_formato_efetivo=(
            (anuncio.formato_frete_produto if anuncio.frete_sobrescrever_loja else (anuncio.loja.formato_frete if anuncio.loja else None))
            or "sem_frete"
        ),
        frete_origem_regra="produto" if anuncio.frete_sobrescrever_loja else "loja",
        frete_gratis=(
            ((anuncio.formato_frete_produto if anuncio.frete_sobrescrever_loja else (anuncio.loja.formato_frete if anuncio.loja else None)) == "gratis")
        ),
        distancia_km=distancia_haversine_km,
        cidade_loja=cli.cidade if cli else None,
        uf_loja=cli.uf if cli else None,
        bairro_loja=None,
        distancia_rota_km=distancia_rota_km,
        duracao_rota_min=duracao_rota_min,
        rota_estimada=rota_estimada,
    )


# --- Público: anúncios "perto de você" (home) — aleatório + ordenação por rota real ---
@router.get("/anuncios/perto-de-voce", response_model=dict)
async def listar_anuncios_perto_de_voce(
    request: Request,
    response: Response,
    lat: float = Query(..., ge=-34, le=6, description="Latitude do morador"),
    lng: float = Query(..., ge=-74, le=-28, description="Longitude do morador"),
    limit: int = Query(12, ge=1, le=24, description="Total a exibir"),
    pool: int = Query(40, ge=10, le=120, description="Tamanho da amostra aleatória antes do refino por rota"),
    bbox_km: float = Query(50.0, gt=0, le=200, description="Raio da bounding box (Haversine) para pré-filtro"),
    loja_slug: Optional[str] = Query(None),
    cliente_ids: Optional[List[int]] = Query(None),
    db: Session = Depends(get_db),
):
    """Faixa "Perto de você" da home: amostra aleatória de anúncios elegíveis ordenada por
    distância de rota real (Google/OSRM) entre o morador e a loja.

    Política de seleção:
      1. Filtra anúncios publicados de lojas ativas com `Cliente.latitude/longitude`.
      2. Pré-filtro por bounding box `bbox_km` em torno do morador (Haversine no banco).
      3. Sorteia aleatoriamente `pool` anúncios diversificados por loja.
      4. Refina com matriz de rota real e ordena por `duração` ascendente; corta em `limit`.
    """
    from sqlalchemy import and_ as _and_, case as _case, func as _func

    from app.services.geo_service import haversine_km
    from app.services.routing_service import distance_matrix

    response.headers["Cache-Control"] = "public, max-age=30"

    # Caixa aproximada (graus) para pré-filtro indexado.
    lat_delta = bbox_km / 110.574
    cos_lat = max(0.000001, math.cos(math.radians(lat)))
    lng_delta = bbox_km / (111.320 * cos_lat)

    query = (
        db.query(AnuncioPlataforma)
        .join(LojaMarketplace)
        .join(Cliente, Cliente.id == LojaMarketplace.cliente_id)
        .filter(
            AnuncioPlataforma.status == "publicado",
            LojaMarketplace.status == "ativo",
            Cliente.latitude.isnot(None),
            Cliente.longitude.isnot(None),
            Cliente.latitude.between(lat - lat_delta, lat + lat_delta),
            Cliente.longitude.between(lng - lng_delta, lng + lng_delta),
        )
    )
    if loja_slug:
        slug_norm = _normalize_loja_slug(loja_slug)
        query = query.filter(_func.lower(LojaMarketplace.slug) == slug_norm)
    if cliente_ids:
        cids = [int(x) for x in cliente_ids if x is not None][:200]
        if cids:
            query = query.filter(LojaMarketplace.cliente_id.in_(cids))

    candidatos = query.order_by(_func.random()).limit(pool * 4).all()
    if not candidatos:
        return {"items": [], "total": 0, "lat": lat, "lng": lng}

    # Diversificar por loja (no maximo 2 anuncios por loja) e respeitar `pool`.
    por_loja: Dict[int, int] = {}
    selecionados: List[AnuncioPlataforma] = []
    for an in candidatos:
        cnt = por_loja.get(an.loja_id, 0)
        if cnt >= 2:
            continue
        por_loja[an.loja_id] = cnt + 1
        selecionados.append(an)
        if len(selecionados) >= pool:
            break
    if not selecionados:
        return {"items": [], "total": 0, "lat": lat, "lng": lng}

    # Carrega Cliente (loja) em batch para evitar N+1.
    cliente_ids_db = list({an.loja.cliente_id for an in selecionados if an.loja and an.loja.cliente_id})
    clientes = db.query(Cliente).filter(Cliente.id.in_(cliente_ids_db)).all()
    cli_por_id: Dict[int, Cliente] = {c.id: c for c in clientes}

    destinos: List[Tuple[float, float]] = []
    indice_destino: List[int] = []
    for i, an in enumerate(selecionados):
        cli = cli_por_id.get(an.loja.cliente_id) if an.loja else None
        if cli and cli.latitude is not None and cli.longitude is not None:
            destinos.append((float(cli.latitude), float(cli.longitude)))
            indice_destino.append(i)

    legs = distance_matrix((lat, lng), destinos) if destinos else []
    leg_por_indice: Dict[int, "RouteLeg"] = {idx: leg for idx, leg in zip(indice_destino, legs)}

    items_calc = []
    for i, an in enumerate(selecionados):
        cli = cli_por_id.get(an.loja.cliente_id) if an.loja else None
        leg = leg_por_indice.get(i)
        dist_h = None
        if cli and cli.latitude is not None and cli.longitude is not None:
            dist_h = round(haversine_km(lat, lng, cli.latitude, cli.longitude), 1)
        rota_km = leg.distance_km if leg else None
        rota_min = leg.duration_min if leg else None
        rota_est = leg.is_estimate if leg else True
        items_calc.append(
            (
                an,
                cli,
                rota_km if rota_km is not None else (dist_h if dist_h is not None else 9999.0),
                rota_min if rota_min is not None else (dist_h if dist_h is not None else 9999.0),
                {
                    "rota_km": rota_km,
                    "rota_min": rota_min,
                    "rota_est": rota_est,
                    "dist_h": dist_h,
                },
            )
        )
    items_calc.sort(key=lambda t: (t[3], t[2]))

    out: List[AnuncioVitrineResponse] = []
    for an, cli, _ord_km, _ord_min, meta in items_calc[:limit]:
        out.append(
            _montar_anuncio_response(
                an,
                cli,
                db,
                distancia_rota_km=meta["rota_km"],
                duracao_rota_min=meta["rota_min"],
                rota_estimada=meta["rota_est"],
                distancia_haversine_km=meta["dist_h"],
            )
        )
    return {"items": out, "total": len(out), "lat": lat, "lng": lng}


# --- Público: anúncios próximos por termo de busca (faixa pós-busca) ---
@router.get("/anuncios/proximos", response_model=dict)
async def listar_anuncios_proximos_por_busca(
    request: Request,
    response: Response,
    q: str = Query(..., min_length=2, max_length=100, description="Termo da busca"),
    lat: float = Query(..., ge=-34, le=6),
    lng: float = Query(..., ge=-74, le=-28),
    limit: int = Query(12, ge=1, le=24),
    top_n_lojas: int = Query(50, ge=10, le=200, description="Top-N lojas mais próximas (Haversine) refinadas com rota"),
    max_km: Optional[float] = Query(None, gt=0, le=500, description="Filtro opcional: descartar se rota exceder N km"),
    bbox_km: float = Query(80.0, gt=0, le=200),
    db: Session = Depends(get_db),
):
    """Faixa pós-busca: lojas mais próximas que vendem o produto buscado.

    Casa o termo em título, descrição, atributos do anúncio e nome/código/categoria do produto.
    Agrupa por loja (escolhe melhor oferta — menor preço efetivo) e ordena por rota real.
    """
    from sqlalchemy import and_ as _and_, case as _case, func as _func

    from app.services.geo_service import haversine_km
    from app.services.routing_service import distance_matrix

    response.headers["Cache-Control"] = "public, max-age=30"

    lat_delta = bbox_km / 110.574
    cos_lat = max(0.000001, math.cos(math.radians(lat)))
    lng_delta = bbox_km / (111.320 * cos_lat)

    preco_efetivo = _case(
        (
            _and_(
                AnuncioPlataforma.preco_promocional.isnot(None),
                AnuncioPlataforma.preco_promocional > 0,
            ),
            AnuncioPlataforma.preco_promocional,
        ),
        else_=AnuncioPlataforma.preco_original,
    )

    query = (
        db.query(AnuncioPlataforma)
        .join(LojaMarketplace)
        .join(Cliente, Cliente.id == LojaMarketplace.cliente_id)
        .join(ProdutoCliente, ProdutoCliente.id == AnuncioPlataforma.produto_ca_id)
        .outerjoin(MaterialCategoria, MaterialCategoria.id == ProdutoCliente.categoria_id)
        .filter(
            AnuncioPlataforma.status == "publicado",
            LojaMarketplace.status == "ativo",
            Cliente.latitude.isnot(None),
            Cliente.longitude.isnot(None),
            Cliente.latitude.between(lat - lat_delta, lat + lat_delta),
            Cliente.longitude.between(lng - lng_delta, lng + lng_delta),
        )
    )

    tokens = [t for t in q.strip().split() if t][:6]
    for tok in tokens:
        term = f"%{tok}%"
        query = query.filter(
            (AnuncioPlataforma.titulo.ilike(term))
            | (AnuncioPlataforma.descricao.ilike(term))
            | (AnuncioPlataforma.atributos.ilike(term))
            | (ProdutoCliente.nome.ilike(term))
            | (ProdutoCliente.descricao.ilike(term))
            | (ProdutoCliente.codigo.ilike(term))
            | (MaterialCategoria.nome.ilike(term))
            | (MaterialCategoria.descricao.ilike(term))
        )

    rows = query.order_by(preco_efetivo.asc(), AnuncioPlataforma.id).all()
    if not rows:
        return {"items": [], "total": 0, "lat": lat, "lng": lng}

    # Uma melhor oferta por loja (preco efetivo asc).
    melhor_por_loja: Dict[int, AnuncioPlataforma] = {}
    for r in rows:
        if r.loja_id not in melhor_por_loja:
            melhor_por_loja[r.loja_id] = r

    # Top-N lojas mais proximas por Haversine.
    cliente_ids_db = list({an.loja.cliente_id for an in melhor_por_loja.values() if an.loja and an.loja.cliente_id})
    clientes = db.query(Cliente).filter(Cliente.id.in_(cliente_ids_db)).all()
    cli_por_id: Dict[int, Cliente] = {c.id: c for c in clientes}

    candidatos = []
    for an in melhor_por_loja.values():
        cli = cli_por_id.get(an.loja.cliente_id) if an.loja else None
        if not cli or cli.latitude is None or cli.longitude is None:
            continue
        dist_h = haversine_km(lat, lng, float(cli.latitude), float(cli.longitude))
        candidatos.append((an, cli, dist_h))
    candidatos.sort(key=lambda t: t[2])
    candidatos = candidatos[:top_n_lojas]
    if not candidatos:
        return {"items": [], "total": 0, "lat": lat, "lng": lng}

    destinos = [(float(cli.latitude), float(cli.longitude)) for (_an, cli, _h) in candidatos]
    legs = distance_matrix((lat, lng), destinos)

    enriched = []
    for (an, cli, dist_h), leg in zip(candidatos, legs):
        ord_min = leg.duration_min if leg.duration_min is not None else (leg.distance_km if leg else dist_h)
        ord_km = leg.distance_km if leg.distance_km is not None else dist_h
        if max_km is not None and ord_km > max_km:
            continue
        enriched.append((an, cli, leg, dist_h, ord_min, ord_km))
    enriched.sort(key=lambda t: (t[4], t[5]))

    out: List[AnuncioVitrineResponse] = []
    for an, cli, leg, dist_h, _ord_min, _ord_km in enriched[:limit]:
        out.append(
            _montar_anuncio_response(
                an,
                cli,
                db,
                distancia_rota_km=leg.distance_km,
                duracao_rota_min=leg.duration_min,
                rota_estimada=leg.is_estimate,
                distancia_haversine_km=round(dist_h, 1),
            )
        )
    return {"items": out, "total": len(out), "lat": lat, "lng": lng}


# --- Público: detalhe anúncio ---
@router.get("/anuncios/{anuncio_id}", response_model=dict)
async def obter_anuncio_vitrine(
    anuncio_id: int,
    db: Session = Depends(get_db),
):
    """Detalhe de um anúncio público (status=publicado)."""
    anuncio = (
        db.query(AnuncioPlataforma)
        .join(LojaMarketplace)
        .filter(
            AnuncioPlataforma.id == anuncio_id,
            AnuncioPlataforma.status == "publicado",
            LojaMarketplace.status == "ativo",
        )
        .first()
    )
    if not anuncio:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado")
    loja = anuncio.loja
    produto_base = db.query(ProdutoCliente).filter(ProdutoCliente.id == anuncio.produto_ca_id).first()
    estoque_vitrine = anuncio.estoque_atual
    if (
        (getattr(anuncio, "tipo_estoque", None) or "").strip().lower() == "sincronizado"
        and produto_base
        and produto_base.quantidade_atual is not None
    ):
        estoque_vitrine = float(produto_base.quantidade_atual)
    return {
        "id": anuncio.id,
        "titulo": anuncio.titulo,
        "descricao": anuncio.descricao,
        "produto_ca_descricao": produto_base.descricao if produto_base else None,
        "categoria_id": produto_base.categoria_id if produto_base else None,
        "imagens": _imagens_anuncio_ou_fallback(anuncio, db),
        "og_image_url": (getattr(anuncio, "og_image_url", None) or "").strip() or None,
        "preco_original": anuncio.preco_original,
        "preco_promocional": anuncio.preco_promocional,
        "estoque_atual": estoque_vitrine,
        "atributos": anuncio.atributos,
        "frete_formato_efetivo": (
            (anuncio.formato_frete_produto if anuncio.frete_sobrescrever_loja else (loja.formato_frete if loja else None))
            or "sem_frete"
        ),
        "frete_origem_regra": "produto" if anuncio.frete_sobrescrever_loja else "loja",
        "frete_gratis": (
            (anuncio.formato_frete_produto if anuncio.frete_sobrescrever_loja else (loja.formato_frete if loja else None)) == "gratis"
        ),
        "loja": {
            "id": loja.id,
            "slug": loja.slug,
            "nome_loja": loja.nome_loja,
            "descricao": loja.descricao,
        } if loja else None,
    }


@router.get("/anuncios/{anuncio_id}/semelhantes", response_model=dict)
async def listar_anuncios_semelhantes(
    anuncio_id: int,
    limit: int = Query(8, ge=1, le=16),
    db: Session = Depends(get_db),
):
    """Lista produtos semelhantes por categoria de estoque do produto base (aleatório)."""
    from sqlalchemy import func

    anuncio_base = (
        db.query(AnuncioPlataforma)
        .join(LojaMarketplace)
        .filter(
            AnuncioPlataforma.id == anuncio_id,
            AnuncioPlataforma.status == "publicado",
            LojaMarketplace.status == "ativo",
        )
        .first()
    )
    if not anuncio_base:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado")
    if anuncio_base.produto_ca_id is None:
        raise HTTPException(
            status_code=409,
            detail="Anúncio sem produto base vinculado para calcular semelhantes",
        )

    produto_base = db.query(ProdutoCliente).filter(ProdutoCliente.id == anuncio_base.produto_ca_id).first()
    if not produto_base:
        raise HTTPException(
            status_code=409,
            detail="Produto base do anúncio não encontrado para calcular semelhantes",
        )

    categoria_id = produto_base.categoria_id
    if categoria_id is None:
        return {
            "items": [],
            "total": 0,
            "limit": limit,
            "categoria_id": None,
            "motivo": "produto_sem_categoria",
        }

    query = (
        db.query(AnuncioPlataforma)
        .join(LojaMarketplace)
        .join(ProdutoCliente, ProdutoCliente.id == AnuncioPlataforma.produto_ca_id)
        .filter(
            AnuncioPlataforma.status == "publicado",
            LojaMarketplace.status == "ativo",
            ProdutoCliente.categoria_id == categoria_id,
            AnuncioPlataforma.id != anuncio_id,
        )
    )
    total = query.count()
    rows = query.order_by(func.random()).limit(limit).all()

    items = []
    for r in rows:
        imgs = _imagens_anuncio_ou_fallback(r, db)
        estoque_sim = r.estoque_atual
        if (getattr(r, "tipo_estoque", None) or "").strip().lower() == "sincronizado":
            pc_s = getattr(r, "produto_cliente", None)
            if pc_s is not None and getattr(pc_s, "quantidade_atual", None) is not None:
                estoque_sim = float(pc_s.quantidade_atual)
        items.append(
            AnuncioVitrineResponse(
                id=r.id,
                titulo=r.titulo,
                loja_id=r.loja_id,
                preco_original=r.preco_original,
                preco_promocional=r.preco_promocional,
                imagens=imgs,
                og_image_url=(getattr(r, "og_image_url", None) or "").strip() or None,
                slug_loja=r.loja.slug if r.loja else None,
                nome_loja=r.loja.nome_loja if r.loja else None,
                estoque_atual=estoque_sim,
                status=r.status,
            )
        )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "categoria_id": categoria_id,
    }


# --- Cadastro e login consumidor ---
class ConsumidorSnippet(BaseModel):
    id: int
    nome: Optional[str] = None
    email: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    consumidor: Optional[ConsumidorSnippet] = None


def _set_consumidor_cookie(response: Response, token: str, request: Optional[Request] = None) -> None:
    if request and request.headers.get("X-Client") == "mobile":
        return
    secure_cookie = os.getenv("HTTPS", "false").lower() in ("true", "1")
    response.set_cookie(
        key=COOKIE_LOJA_CONSUMIDOR,
        value=token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )


def _decode_jwt_payload_no_verify(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload_b64 = parts[1]
        padding = "=" * (-len(payload_b64) % 4)
        decoded = base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return {}


def _normalize_provider(provider: str) -> str:
    p = (provider or "").strip().lower()
    if p not in {"google", "facebook", "apple"}:
        raise HTTPException(status_code=400, detail="Provider inválido. Use google, facebook ou apple.")
    return p


def _extract_google_profile(id_token: Optional[str], access_token: Optional[str]) -> dict:
    if id_token:
        claims = _decode_jwt_payload_no_verify(id_token)
        return {
            "provider_user_id": claims.get("sub"),
            "email": claims.get("email"),
            "email_verified": bool(claims.get("email_verified")),
            "nome": claims.get("name"),
            "avatar_url": claims.get("picture"),
        }
    if not access_token:
        raise HTTPException(status_code=400, detail="Token do provider ausente")
    try:
        with httpx.Client(timeout=8.0) as client:
            r = client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="Falha ao validar token do Google")
        data = r.json()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao consultar perfil social")
    return {
        "provider_user_id": data.get("sub"),
        "email": data.get("email"),
        "email_verified": bool(data.get("email_verified")),
        "nome": data.get("name"),
        "avatar_url": data.get("picture"),
    }


def _extract_facebook_profile(access_token: Optional[str]) -> dict:
    if not access_token:
        raise HTTPException(status_code=400, detail="Token do provider ausente")
    try:
        with httpx.Client(timeout=8.0) as client:
            r = client.get(
                "https://graph.facebook.com/me",
                params={"fields": "id,name,email,picture.type(large)", "access_token": access_token},
            )
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="Falha ao validar token do Facebook")
        data = r.json()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao consultar perfil social")
    pic = data.get("picture") or {}
    pic_data = pic.get("data") if isinstance(pic, dict) else {}
    return {
        "provider_user_id": data.get("id"),
        "email": data.get("email"),
        "email_verified": bool(data.get("email")),
        "nome": data.get("name"),
        "avatar_url": pic_data.get("url") if isinstance(pic_data, dict) else None,
    }


def _extract_apple_profile(id_token: Optional[str]) -> dict:
    if not id_token:
        raise HTTPException(status_code=400, detail="id_token é obrigatório para Apple")
    claims = _decode_jwt_payload_no_verify(id_token)
    return {
        "provider_user_id": claims.get("sub"),
        "email": claims.get("email"),
        "email_verified": str(claims.get("email_verified", "")).lower() in {"true", "1"},
        "nome": claims.get("name"),
        "avatar_url": None,
    }


def _fetch_social_profile(provider: str, id_token: Optional[str], access_token: Optional[str]) -> dict:
    if provider == "google":
        return _extract_google_profile(id_token=id_token, access_token=access_token)
    if provider == "facebook":
        return _extract_facebook_profile(access_token=access_token)
    return _extract_apple_profile(id_token=id_token)


@router.post("/cadastro", status_code=status.HTTP_201_CREATED)
async def cadastrar_consumidor(
    body: ConsumidorCadastro,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(check_loja_cadastro_rate_limit),
):
    """Cadastro de consumidor (cliente final) na vitrine. Opcional loja_id para escopo tenant."""
    if not body.aceite_termos:
        raise HTTPException(status_code=400, detail="É necessário aceitar os termos")
    email_norm = body.email.strip().lower()
    tenant_id = None
    if body.loja_id:
        loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == body.loja_id).first()
        if loja:
            tenant_id = loja.cliente_id
    if tenant_id is not None:
        from sqlalchemy import func
        existente = (
            db.query(ConsumidorMarketplace)
            .filter(
                ConsumidorMarketplace.tenant_id == tenant_id,
                func.lower(ConsumidorMarketplace.email) == email_norm,
                ConsumidorMarketplace.deleted_at.is_(None),
            )
            .first()
        )
    else:
        existente = db.query(ConsumidorMarketplace).filter(
            ConsumidorMarketplace.email == email_norm,
            ConsumidorMarketplace.deleted_at.is_(None),
        ).first()
    if existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    senha_hash = AuthConfig.get_password_hash(body.senha)
    consumidor = ConsumidorMarketplace(
        tenant_id=tenant_id,
        email=email_norm,
        senha_hash=senha_hash,
        nome=body.nome.strip()[:200],
        telefone=body.telefone.strip()[:20] if body.telefone else None,
        documento=body.documento.strip()[:20] if body.documento else None,
        aceite_termos=body.aceite_termos,
        ativo=True,
        tipo_consumidor="REGISTERED",
        status_cadastro="COMPLETO",
    )
    db.add(consumidor)
    db.commit()
    db.refresh(consumidor)
    access_token = create_consumidor_token(consumidor.id)
    refresh_raw, _ = create_consumidor_refresh_token(db, consumidor.id, device_info="cadastro")
    _set_consumidor_cookie(response, access_token, request)
    return {
        "access_token": access_token,
        "refresh_token": refresh_raw,
        "token_type": "bearer",
        "consumidor": ConsumidorResponse.model_validate(consumidor).model_dump(),
    }


@router.post("/login", response_model=TokenResponse)
async def login_consumidor(
    body: ConsumidorLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(check_loja_login_rate_limit),
):
    """Login do consumidor. Opcional loja_id para escopo tenant (tenant_id + email)."""
    from sqlalchemy import func
    email_norm = body.email.strip().lower()
    if body.loja_id:
        loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == body.loja_id).first()
        if loja:
            consumidor = (
                db.query(ConsumidorMarketplace)
                .filter(
                    ConsumidorMarketplace.tenant_id == loja.cliente_id,
                    func.lower(ConsumidorMarketplace.email) == email_norm,
                    ConsumidorMarketplace.deleted_at.is_(None),
                )
                .first()
            )
            if not consumidor:
                consumidor = (
                    db.query(ConsumidorMarketplace)
                    .filter(
                        ConsumidorMarketplace.tenant_id.is_(None),
                        func.lower(ConsumidorMarketplace.email) == email_norm,
                        ConsumidorMarketplace.deleted_at.is_(None),
                    )
                    .first()
                )
        else:
            consumidor = None
    else:
        consumidor = db.query(ConsumidorMarketplace).filter(
            func.lower(ConsumidorMarketplace.email) == email_norm,
            ConsumidorMarketplace.deleted_at.is_(None),
        ).first()
    if not consumidor or not consumidor.ativo:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")
    if not consumidor.senha_hash or not AuthConfig.verify_password(body.senha, consumidor.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")
    access_token = create_consumidor_token(consumidor.id)
    refresh_raw, _ = create_consumidor_refresh_token(db, consumidor.id, device_info="login")
    _set_consumidor_cookie(response, access_token, request)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_raw,
        consumidor=ConsumidorSnippet(id=consumidor.id, nome=consumidor.nome, email=consumidor.email),
    )


@router.post("/auth/social/login", response_model=ConsumidorSocialLoginResponse)
async def login_social_consumidor(
    body: ConsumidorSocialLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(check_loja_login_rate_limit),
):
    from sqlalchemy import func

    provider = _normalize_provider(body.provider)
    profile = _fetch_social_profile(provider, body.id_token, body.access_token)
    provider_user_id = (profile.get("provider_user_id") or "").strip()
    if not provider_user_id:
        raise HTTPException(status_code=400, detail="Não foi possível identificar o usuário no provedor")

    email_raw = (profile.get("email") or "").strip().lower()
    if not email_raw:
        raise HTTPException(status_code=400, detail="Provedor não retornou e-mail. Complete o cadastro manualmente.")

    identity = db.query(ConsumidorSocialIdentity).filter(
        ConsumidorSocialIdentity.provider == provider,
        ConsumidorSocialIdentity.provider_user_id == provider_user_id,
    ).first()
    if identity:
        consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.id == identity.consumidor_id).first()
        if not consumidor or not consumidor.ativo:
            raise HTTPException(status_code=401, detail="Conta de consumidor inativa")
        access_token = create_consumidor_token(consumidor.id)
        refresh_raw, _ = create_consumidor_refresh_token(db, consumidor.id, device_info=f"social_{provider}")
        _set_consumidor_cookie(response, access_token, request)
        return ConsumidorSocialLoginResponse(
            status="authenticated",
            access_token=access_token,
            refresh_token=refresh_raw,
            token_type="bearer",
            consumidor=ConsumidorResponse.model_validate(consumidor),
        )

    consumidor_existente = db.query(ConsumidorMarketplace).filter(
        func.lower(ConsumidorMarketplace.email) == email_raw,
        ConsumidorMarketplace.deleted_at.is_(None),
    ).first()

    if consumidor_existente:
        raw_link_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_link_token.encode("utf-8")).hexdigest()
        pending = ConsumidorSocialLinkPending(
            consumidor_id=consumidor_existente.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email_provider=email_raw,
            email_verified=bool(profile.get("email_verified")),
            nome_provider=(profile.get("nome") or None),
            avatar_url=(profile.get("avatar_url") or None),
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            metadata_json=json.dumps({"provider": provider}, ensure_ascii=False),
        )
        db.add(pending)
        db.commit()
        tem_senha = bool(consumidor_existente.senha_hash)
        msg_link = (
            "E-mail já cadastrado. Confirme sua senha para vincular a conta social."
            if tem_senha
            else "E-mail já cadastrado. Sua conta não tem senha para login por e-mail. Confirme o vínculo abaixo (você já se autenticou no provedor). Depois, em Esqueci minha senha, você pode criar uma senha se quiser."
        )
        return ConsumidorSocialLoginResponse(
            status="pending_link",
            link_token=raw_link_token,
            message=msg_link,
            requires_password=tem_senha,
        )

    if not body.aceite_termos:
        raise HTTPException(status_code=400, detail="É necessário aceitar os termos")
    nome = (profile.get("nome") or body.nome_fallback or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome obrigatório para concluir o cadastro social")

    consumidor = ConsumidorMarketplace(
        tenant_id=None,
        email=email_raw,
        senha_hash=None,
        nome=nome[:200],
        aceite_termos=True,
        ativo=True,
        tipo_consumidor="REGISTERED",
        status_cadastro="COMPLETO",
        origem_social_provider=provider,
        email_verificado=bool(profile.get("email_verified")),
        avatar_url=(profile.get("avatar_url") or None),
    )
    db.add(consumidor)
    db.flush()
    db.add(
        ConsumidorSocialIdentity(
            consumidor_id=consumidor.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email_provider=email_raw,
            email_verified=bool(profile.get("email_verified")),
            nome_provider=(profile.get("nome") or None),
            avatar_url=(profile.get("avatar_url") or None),
        )
    )
    db.commit()
    db.refresh(consumidor)
    access_token = create_consumidor_token(consumidor.id)
    refresh_raw, _ = create_consumidor_refresh_token(db, consumidor.id, device_info=f"social_{provider}_new")
    _set_consumidor_cookie(response, access_token, request)
    return ConsumidorSocialLoginResponse(
        status="authenticated",
        access_token=access_token,
        refresh_token=refresh_raw,
        token_type="bearer",
        consumidor=ConsumidorResponse.model_validate(consumidor),
    )


@router.post("/auth/social/confirm-link", response_model=ConsumidorSocialLoginResponse)
async def confirmar_link_social_consumidor(
    body: ConsumidorSocialConfirmLink,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(check_loja_login_rate_limit),
):
    token_hash = hashlib.sha256(body.link_token.encode("utf-8")).hexdigest()
    pending = db.query(ConsumidorSocialLinkPending).filter(
        ConsumidorSocialLinkPending.token_hash == token_hash,
    ).first()
    if not pending:
        raise HTTPException(status_code=400, detail="Token de vínculo inválido")
    now = datetime.now(timezone.utc)
    if pending.used_at is not None or pending.expires_at < now:
        raise HTTPException(status_code=400, detail="Token de vínculo expirado ou já utilizado")

    consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.id == pending.consumidor_id).first()
    if not consumidor or not consumidor.ativo:
        raise HTTPException(status_code=404, detail="Consumidor não encontrado")
    if consumidor.senha_hash:
        if not (body.senha or "").strip():
            raise HTTPException(status_code=400, detail="Informe sua senha para confirmar o vínculo.")
        if not AuthConfig.verify_password(body.senha, consumidor.senha_hash):
            raise HTTPException(status_code=401, detail="Senha inválida para confirmar vínculo")
    # Conta sem senha local: o link_token já foi emitido na mesma sessão após OAuth com o mesmo e-mail do cadastro.

    existente = db.query(ConsumidorSocialIdentity).filter(
        ConsumidorSocialIdentity.provider == pending.provider,
        ConsumidorSocialIdentity.provider_user_id == pending.provider_user_id,
    ).first()
    if existente:
        pending.used_at = now
        db.commit()
        raise HTTPException(status_code=409, detail="Conta social já vinculada a outro consumidor")

    db.add(
        ConsumidorSocialIdentity(
            consumidor_id=consumidor.id,
            provider=pending.provider,
            provider_user_id=pending.provider_user_id,
            email_provider=pending.email_provider,
            email_verified=bool(pending.email_verified),
            nome_provider=pending.nome_provider,
            avatar_url=pending.avatar_url,
        )
    )
    if pending.email_verified:
        consumidor.email_verificado = True
    if not consumidor.origem_social_provider:
        consumidor.origem_social_provider = pending.provider
    if pending.avatar_url and not consumidor.avatar_url:
        consumidor.avatar_url = pending.avatar_url
    pending.used_at = now
    db.commit()
    db.refresh(consumidor)

    access_token = create_consumidor_token(consumidor.id)
    refresh_raw, _ = create_consumidor_refresh_token(db, consumidor.id, device_info=f"social_link_{pending.provider}")
    _set_consumidor_cookie(response, access_token, request)
    return ConsumidorSocialLoginResponse(
        status="authenticated",
        access_token=access_token,
        refresh_token=refresh_raw,
        token_type="bearer",
        consumidor=ConsumidorResponse.model_validate(consumidor),
    )


@router.post("/logout")
async def logout_consumidor(response: Response):
    """Remove o cookie de autenticação do consumidor."""
    response.delete_cookie(key=COOKIE_LOJA_CONSUMIDOR)
    return {"detail": "Logout realizado"}


MESSAGE_FORGOT_PASSWORD_LOJA = (
    "Se este e-mail estiver cadastrado, você receberá um link para redefinir sua senha."
)


class ForgotPasswordLojaBody(BaseModel):
    email: str
    loja_id: Optional[int] = None


class ResetPasswordLojaBody(BaseModel):
    token: str
    new_password: str
    confirm_password: str


@router.post("/forgot-password")
async def forgot_password_loja(
    request: Request,
    body: ForgotPasswordLojaBody,
    db: Session = Depends(get_db),
):
    """Solicita redefinição de senha (Esqueci minha senha) - consumidor da loja."""
    await check_forgot_password_rate_limit(request)
    base_url = _public_base_url_for_checkout(request)
    request_reset_loja(db, body.email, base_url=base_url, loja_id=body.loja_id)
    return {"message": MESSAGE_FORGOT_PASSWORD_LOJA}


@router.get("/redefinir-senha/valida")
async def redefinir_senha_loja_valida(
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Verifica se o token de redefinição (loja) é válido."""
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token ausente.")
    valid = validate_token_loja(db, token)
    return {"valid": valid}


@router.post("/redefinir-senha")
async def redefinir_senha_loja(
    request: Request,
    body: ResetPasswordLojaBody,
    db: Session = Depends(get_db),
):
    """Redefine a senha do consumidor usando o token enviado por e-mail."""
    await check_reset_password_rate_limit(request)
    success, error_msg = reset_password_loja(db, body.token, body.new_password, body.confirm_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    return {"message": "Senha alterada com sucesso. Faça login com a nova senha."}


# --- Minha conta (autenticado consumidor) ---
@router.get("/minha-conta", response_model=ConsumidorResponse)
async def minha_conta(
    consumidor: ConsumidorMarketplace = Depends(get_current_consumidor),
):
    return ConsumidorResponse.model_validate(consumidor)


@router.put("/minha-conta", response_model=ConsumidorResponse)
async def atualizar_minha_conta(
    body: ConsumidorUpdate,
    db: Session = Depends(get_db),
    consumidor: ConsumidorMarketplace = Depends(get_current_consumidor),
):
    from datetime import datetime, timezone
    aceite_antes = getattr(consumidor, "aceite_marketing", None)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(consumidor, k, v)
    if body.aceite_marketing is not None and consumidor.aceite_marketing != aceite_antes:
        consumidor.aceite_marketing_em = datetime.now(timezone.utc)
    if body.aceite_marketing is not None and consumidor.aceite_marketing != aceite_antes and consumidor.tenant_id:
        emit_integration_event(
            db,
            tenant_id=consumidor.tenant_id,
            event_name="consumer.marketing_optin_changed",
            entity_type="consumer",
            entity_id=consumidor.id,
            payload={
                "id": consumidor.id,
                "aceite_marketing": consumidor.aceite_marketing,
                "updated_at": consumidor.updated_at.isoformat() if getattr(consumidor, "updated_at", None) else None,
            },
        )
    db.commit()
    db.refresh(consumidor)
    return ConsumidorResponse.model_validate(consumidor)


# --- Endereços consumidor ---
@router.get("/minha-conta/enderecos", response_model=List[EnderecoConsumidorResponse])
async def listar_meus_enderecos(
    db: Session = Depends(get_db),
    consumidor: ConsumidorMarketplace = Depends(get_current_consumidor),
):
    rows = db.query(EnderecoConsumidor).filter(EnderecoConsumidor.consumidor_id == consumidor.id).all()
    return [EnderecoConsumidorResponse.model_validate(r) for r in rows]


@router.post("/minha-conta/enderecos", response_model=EnderecoConsumidorResponse, status_code=status.HTTP_201_CREATED)
async def criar_endereco(
    body: EnderecoConsumidorCreate,
    db: Session = Depends(get_db),
    consumidor: ConsumidorMarketplace = Depends(get_current_consumidor),
):
    end = EnderecoConsumidor(
        tenant_id=consumidor.tenant_id,
        consumidor_id=consumidor.id,
        apelido=body.apelido,
        cep=body.cep,
        logradouro=body.logradouro,
        numero=body.numero,
        complemento=body.complemento,
        bairro=body.bairro,
        cidade=body.cidade,
        uf=body.uf,
        tipo_endereco=body.tipo_endereco or "principal",
        referencia=body.referencia,
        principal=body.principal,
    )
    db.add(end)
    db.commit()
    db.refresh(end)
    if end.cep:
        try:
            from app.worker.geo_tasks import geocode_endereco
            geocode_endereco.delay("enderecos_consumidor", end.id, end.cep)
        except Exception:
            pass
    return EnderecoConsumidorResponse.model_validate(end)


@router.patch("/minha-conta/enderecos/{endereco_id}", response_model=EnderecoConsumidorResponse)
async def atualizar_endereco(
    endereco_id: int,
    body: EnderecoConsumidorCreate,
    db: Session = Depends(get_db),
    consumidor: ConsumidorMarketplace = Depends(get_current_consumidor),
):
    end = db.query(EnderecoConsumidor).filter(
        EnderecoConsumidor.id == endereco_id,
        EnderecoConsumidor.consumidor_id == consumidor.id,
    ).first()
    if not end:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")
    for field in ("apelido", "cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf", "referencia"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(end, field, val)
    if body.tipo_endereco:
        end.tipo_endereco = body.tipo_endereco
    cep_mudou = body.cep is not None
    db.commit()
    db.refresh(end)
    if cep_mudou and end.cep:
        try:
            from app.worker.geo_tasks import geocode_endereco
            geocode_endereco.delay("enderecos_consumidor", end.id, end.cep)
        except Exception:
            pass
    return EnderecoConsumidorResponse.model_validate(end)


@router.delete("/minha-conta/enderecos/{endereco_id}", status_code=204)
async def remover_endereco(
    endereco_id: int,
    db: Session = Depends(get_db),
    consumidor: ConsumidorMarketplace = Depends(get_current_consumidor),
):
    end = db.query(EnderecoConsumidor).filter(
        EnderecoConsumidor.id == endereco_id,
        EnderecoConsumidor.consumidor_id == consumidor.id,
    ).first()
    if not end:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")
    pendentes = (
        db.query(PedidoMarketplace)
        .filter(
            PedidoMarketplace.comprador_id == consumidor.id,
            PedidoMarketplace.status_pedido.in_(["aguardando_pagamento", "pago", "em_preparacao", "em_transito"]),
        )
        .count()
    )
    if pendentes > 0 and end.principal:
        raise HTTPException(status_code=400, detail="Não é possível remover endereço principal com pedidos em andamento")
    db.delete(end)
    db.commit()


@router.patch("/minha-conta/enderecos/{endereco_id}/padrao", response_model=EnderecoConsumidorResponse)
async def marcar_endereco_padrao(
    endereco_id: int,
    db: Session = Depends(get_db),
    consumidor: ConsumidorMarketplace = Depends(get_current_consumidor),
):
    end = db.query(EnderecoConsumidor).filter(
        EnderecoConsumidor.id == endereco_id,
        EnderecoConsumidor.consumidor_id == consumidor.id,
    ).first()
    if not end:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")
    db.query(EnderecoConsumidor).filter(
        EnderecoConsumidor.consumidor_id == consumidor.id,
        EnderecoConsumidor.principal.is_(True),
    ).update({"principal": False}, synchronize_session=False)
    end.principal = True
    db.commit()
    db.refresh(end)
    return EnderecoConsumidorResponse.model_validate(end)


# --- Meus pedidos ---
class PedidoItemResumo(BaseModel):
    anuncio_id: int
    titulo: str
    quantidade: float
    preco_unitario: float
    subtotal: float


class PedidoResumo(BaseModel):
    id: int
    numero_pedido: str
    loja_id: int
    status_pedido: str
    status_pagamento: str
    status_entrega: str
    subtotal: float
    desconto: float
    taxa_entrega: float
    total: float
    created_at: Optional[str] = None
    itens: List[PedidoItemResumo] = []


@router.get("/meus-pedidos", response_model=List[PedidoResumo])
async def meus_pedidos(
    db: Session = Depends(get_db),
    consumidor: ConsumidorMarketplace = Depends(get_current_consumidor),
):
    """Lista pedidos do consumidor logado."""
    from sqlalchemy.orm import joinedload
    pedidos = (
        db.query(PedidoMarketplace)
        .filter(PedidoMarketplace.comprador_id == consumidor.id)
        .order_by(PedidoMarketplace.created_at.desc())
        .all()
    )
    result = []
    for p in pedidos:
        itens = (
            db.query(PedidoItemMarketplace)
            .options(joinedload(PedidoItemMarketplace.anuncio))
            .filter(PedidoItemMarketplace.pedido_id == p.id)
            .all()
        )
        itens_resumo = [
            PedidoItemResumo(
                anuncio_id=item.anuncio_id,
                titulo=getattr(item, "nome_produto_snapshot", None) or (item.anuncio.titulo if item.anuncio else ""),
                quantidade=float(item.quantidade),
                preco_unitario=float(item.preco_unitario or 0),
                subtotal=float(item.preco_total or 0),
            )
            for item in itens
        ]
        result.append(
            PedidoResumo(
                id=p.id,
                numero_pedido=getattr(p, "numero_pedido", "") or f"{getattr(p, 'tenant_id', '')}-{p.id}",
                loja_id=p.loja_id,
                status_pedido=p.status_pedido or "",
                status_pagamento=p.status_pagamento or "",
                status_entrega=getattr(p, "status_entrega", "") or "pendente",
                subtotal=float(p.subtotal or 0),
                desconto=float(p.desconto or 0),
                taxa_entrega=float(p.taxa_entrega or 0),
                total=float(p.total or 0),
                created_at=p.created_at.isoformat() if getattr(p.created_at, "isoformat", None) else None,
                itens=itens_resumo,
            )
        )
    return result


# --- Avaliações (pós-compra) ---
@router.post("/pedidos/{pedido_id}/avaliar", response_model=AvaliacaoResponse, status_code=status.HTTP_201_CREATED)
async def criar_avaliacao(
    pedido_id: int,
    body: AvaliacaoCreate,
    db: Session = Depends(get_db),
    consumidor: ConsumidorMarketplace = Depends(get_current_consumidor),
):
    """Avalia um ou mais itens do pedido. Apenas o comprador do pedido pode avaliar."""
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    if pedido.comprador_id != consumidor.id:
        raise HTTPException(status_code=403, detail="Só o comprador pode avaliar este pedido")
    itens = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == pedido_id).all()
    if not itens:
        raise HTTPException(status_code=400, detail="Pedido sem itens")
    item = itens[0]
    existente = db.query(AvaliacaoMarketplace).filter(
        AvaliacaoMarketplace.pedido_id == pedido_id,
        AvaliacaoMarketplace.anuncio_id == item.anuncio_id,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Este pedido já foi avaliado para este produto")
    av = AvaliacaoMarketplace(
        pedido_id=pedido_id,
        anuncio_id=item.anuncio_id,
        loja_id=pedido.loja_id,
        comprador_nome=consumidor.nome,
        nota=body.nota,
        comentario=body.comentario,
    )
    db.add(av)
    db.commit()
    db.refresh(av)
    return AvaliacaoResponse.model_validate(av)


@router.get("/anuncios/{anuncio_id}/avaliacoes", response_model=List[AvaliacaoResponse])
async def listar_avaliacoes_anuncio(
    anuncio_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lista avaliações públicas do anúncio (vitrine)."""
    anuncio = db.query(AnuncioPlataforma).filter(
        AnuncioPlataforma.id == anuncio_id,
        AnuncioPlataforma.status == "publicado",
    ).first()
    if not anuncio:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado")
    rows = (
        db.query(AvaliacaoMarketplace)
        .filter(AvaliacaoMarketplace.anuncio_id == anuncio_id)
        .order_by(AvaliacaoMarketplace.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [AvaliacaoResponse.model_validate(r) for r in rows]


# --- Checkout (criar pedido + baixa de estoque) ---
@router.post("/checkout", response_model=PedidoCheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout(
    request: Request,
    body: PedidoCheckoutCreate,
    db: Session = Depends(get_db),
    consumidor: Optional[ConsumidorMarketplace] = Depends(get_current_consumidor_optional),
    _: None = Depends(check_loja_checkout_rate_limit),
):
    """Cria pedido na loja. Se gateway ativo: reserva estoque e retorna redirect_url. Senão: baixa estoque e redireciona para obrigado."""
    body = _merge_checkout_single_attribution(request, body)
    from datetime import datetime, timezone

    from app.services.payments.checkout_marketplace_service import create_checkout_for_pedido
    from app.services.payments.factory import get_provider_for_cliente

    from ...services.marketplace_checkout_pedido_service import (
        criar_pedido_marketplace_checkout,
        resolve_comprador_para_loja,
    )

    itens_agrupados: dict[int, int] = defaultdict(int)
    for item in body.itens:
        itens_agrupados[item.anuncio_id] += item.quantidade
    if not itens_agrupados:
        raise HTTPException(status_code=400, detail="Nenhum item no pedido")

    loja = db.query(LojaMarketplace).filter(
        LojaMarketplace.id == body.loja_id,
        LojaMarketplace.status == "ativo",
    ).first()
    if not loja:
        raise HTTPException(status_code=404, detail="Loja não encontrada ou inativa")

    if not body.aceite_politica_privacidade:
        raise HTTPException(
            status_code=400,
            detail="É necessário aceitar a Política de Privacidade para finalizar o pedido.",
        )

    tenant_id = loja.cliente_id

    # Idempotência: se mesma chave em 24h, devolve pedido existente
    idem_key = getattr(body, "idempotency_key", None)
    if idem_key and (idem_key := str(idem_key).strip()):
        from datetime import timedelta

        from sqlalchemy import and_
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        existing = (
            db.query(PedidoMarketplace)
            .filter(
                and_(
                    PedidoMarketplace.tenant_id == tenant_id,
                    PedidoMarketplace.loja_id == body.loja_id,
                    PedidoMarketplace.idempotency_key == idem_key,
                    PedidoMarketplace.created_at >= cutoff,
                )
            )
            .order_by(PedidoMarketplace.id.desc())
            .first()
        )
        if existing:
            redirect_url = None
            tx = None
            pr_dict: Optional[dict] = None
            if existing.status_pagamento == "pendente" and existing.transaction_id:
                tx = db.query(PaymentTransaction).filter(
                    PaymentTransaction.pedido_id == existing.id,
                    PaymentTransaction.is_active.is_(True),
                ).order_by(PaymentTransaction.id.desc()).first()
                if tx and tx.provider_response:
                    try:
                        pr_dict = json.loads(tx.provider_response)
                        redirect_url = pr_dict.get("redirect_url")
                    except Exception:
                        pass
            return PedidoCheckoutResponse(
                id=existing.id,
                numero_pedido=existing.numero_pedido,
                loja_id=existing.loja_id,
                status_pedido=existing.status_pedido or "",
                status_pagamento=existing.status_pagamento or "",
                status_entrega=getattr(existing, "status_entrega", "") or "pendente",
                total=existing.total,
                comprador_email=existing.comprador_email,
                created_at=existing.created_at,
                redirect_url=redirect_url,
                transaction_uuid=str(tx.uuid) if tx else existing.transaction_id,
                checkout_type=(pr_dict or {}).get("checkout_type"),
                qr_code=(pr_dict or {}).get("qr_code"),
                copy_paste_code=(pr_dict or {}).get("copy_paste_code"),
                pix=_marketplace_pix_from_stored_response(pr_dict),
            )

    comprador, consumidor_created = resolve_comprador_para_loja(db, loja, body, consumidor)
    pedido = criar_pedido_marketplace_checkout(db, loja, body, comprador, consumidor_created)

    config_gateway, _ = get_provider_for_cliente(db, tenant_id)
    empresa_fiscal = (
        db.query(Empresa)
        .filter(Empresa.cliente_id == tenant_id, Empresa.ativo.is_(True))
        .first()
    )
    modo_plataforma = (
        empresa_fiscal is not None
        and (empresa_fiscal.modo_recebimento or "").strip().lower() == "plataforma"
    )
    if config_gateway or modo_plataforma:
        base_url = _public_base_url_for_checkout(request)
        back_success = f"{base_url}/loja/pagamento/sucesso?pedido={pedido.id}" if base_url else None
        back_cancel = f"{base_url}/loja/pagamento/cancelado?pedido={pedido.id}" if base_url else None
        try:
            out = create_checkout_for_pedido(
                db,
                pedido.id,
                getattr(body, "payment_method", "pix") or "pix",
                back_url_success=back_success,
                back_url_cancel=back_cancel,
                base_url=base_url,
            )
            db.refresh(pedido)
            return PedidoCheckoutResponse(
                id=pedido.id,
                numero_pedido=pedido.numero_pedido,
                loja_id=pedido.loja_id,
                status_pedido=pedido.status_pedido,
                status_pagamento=pedido.status_pagamento,
                status_entrega=pedido.status_entrega,
                subtotal=pedido.subtotal,
                desconto=pedido.desconto,
                taxa_entrega=pedido.taxa_entrega,
                total=pedido.total,
                comprador_email=pedido.comprador_email,
                created_at=pedido.created_at,
                redirect_url=out.get("redirect_url"),
                transaction_uuid=out.get("transaction_uuid"),
                checkout_type=out.get("checkout_type"),
                qr_code=out.get("qr_code"),
                copy_paste_code=out.get("copy_paste_code"),
                pix=out.get("pix"),
            )
        except Exception as e:
            db.rollback()
            from ...core.logging import log_error
            log_error(f"checkout gateway erro: {e} (pedido_id={pedido.id}, loja_id={body.loja_id})", exc_info=True)
            raise HTTPException(status_code=502, detail="Falha ao conectar ao gateway de pagamento. Tente novamente em instantes.")

    from app.services.reserva_estoque_marketplace_service import deduct_marketplace_pedido_stock_committed

    for it in (
        db.query(PedidoItemMarketplace)
        .filter(PedidoItemMarketplace.pedido_id == pedido.id)
        .all()
    ):
        anuncio = (
            db.query(AnuncioPlataforma)
            .filter(AnuncioPlataforma.id == it.anuncio_id)
            .first()
        )
        if not anuncio:
            continue
        qty = it.quantidade
        anuncio.vendas = (anuncio.vendas or 0) + qty
    deduct_marketplace_pedido_stock_committed(db, pedido.id)

    loja.total_vendas_marketplace = (loja.total_vendas_marketplace or 0) + 1
    loja.faturamento_total = (loja.faturamento_total or 0) + float(pedido.total)

    extrato = ExtratoLoja(
        loja_id=body.loja_id,
        pedido_id=pedido.id,
        tipo="venda",
        descricao=f"Pedido #{pedido.numero_pedido}",
        valor_bruto=pedido.total,
        valor_taxa=None,
        valor_liquido=pedido.total,
        valor_frete_cliente=pedido.taxa_entrega,
        status="pendente",
    )
    db.add(extrato)

    db.commit()
    db.refresh(pedido)

    try:
        from app.worker.tasks import emitir_nfe_pedido_marketplace, notificar_ca_novo_pedido
        emitir_nfe_pedido_marketplace.delay(pedido.id)
        notificar_ca_novo_pedido.delay(pedido.id)
    except Exception:
        pass

    return PedidoCheckoutResponse(
        id=pedido.id,
        numero_pedido=pedido.numero_pedido,
        loja_id=pedido.loja_id,
        status_pedido=pedido.status_pedido,
        status_pagamento=pedido.status_pagamento,
        status_entrega=pedido.status_entrega,
        subtotal=pedido.subtotal,
        desconto=pedido.desconto,
        taxa_entrega=pedido.taxa_entrega,
        total=pedido.total,
        comprador_email=pedido.comprador_email,
        created_at=pedido.created_at,
    )


@router.post("/checkout-unificado", response_model=PedidoCheckoutUnificadoResponse, status_code=status.HTTP_201_CREATED)
async def checkout_unificado(
    request: Request,
    body: PedidoCheckoutUnificadoCreate,
    db: Session = Depends(get_db),
    consumidor: Optional[ConsumidorMarketplace] = Depends(get_current_consumidor_optional),
    _: None = Depends(check_loja_checkout_rate_limit),
):
    """Vários pedidos (um por loja), um pagamento no gateway (modo plataforma)."""
    from app.services.payments.checkout_marketplace_service import create_checkout_for_session

    from ...services.marketplace_checkout_pedido_service import (
        criar_pedido_marketplace_checkout,
        resolve_comprador_para_loja,
    )

    body = _merge_checkout_unificado_attribution(request, body)

    grupos: Dict[int, List[CheckoutItem]] = defaultdict(list)
    for it in body.itens:
        grupos[it.loja_id].append(CheckoutItem(anuncio_id=it.anuncio_id, quantidade=it.quantidade))
    loja_ids = sorted(grupos.keys())
    if not loja_ids:
        raise HTTPException(status_code=400, detail="Nenhum item no pedido")

    if not body.aceite_politica_privacidade:
        raise HTTPException(
            status_code=400,
            detail="É necessário aceitar a Política de Privacidade para finalizar o pedido.",
        )

    _lojas_modo_plataforma_obrigatorio_unificado(db, loja_ids)

    idem_key = getattr(body, "idempotency_key", None)
    if idem_key and (idem_key := str(idem_key).strip()):
        from sqlalchemy import and_

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        existing_sess = (
            db.query(MarketplaceCheckoutSession)
            .filter(
                and_(
                    MarketplaceCheckoutSession.idempotency_key == idem_key,
                    MarketplaceCheckoutSession.created_at >= cutoff,
                )
            )
            .order_by(MarketplaceCheckoutSession.id.desc())
            .first()
        )
        if existing_sess:
            links = (
                db.query(MarketplaceCheckoutSessionPedido)
                .filter(MarketplaceCheckoutSessionPedido.session_id == existing_sess.id)
                .order_by(MarketplaceCheckoutSessionPedido.sort_order.asc())
                .all()
            )
            pedidos_rows = [
                db.query(PedidoMarketplace).filter(PedidoMarketplace.id == link.pedido_id).first() for link in links
            ]
            pedidos_rows = [p for p in pedidos_rows if p]
            redirect_url = None
            tx = (
                db.query(PaymentTransaction)
                .filter(
                    PaymentTransaction.checkout_session_id == existing_sess.id,
                    PaymentTransaction.is_active.is_(True),
                )
                .order_by(PaymentTransaction.id.desc())
                .first()
            )
            pr_dict: Optional[dict] = None
            if tx and tx.provider_response:
                try:
                    pr_dict = json.loads(tx.provider_response)
                    redirect_url = pr_dict.get("redirect_url")
                except Exception:
                    pass
            return PedidoCheckoutUnificadoResponse(
                session_uuid=existing_sess.uuid,
                pedidos=[
                    PedidoResumoUnificado(
                        id=p.id,
                        numero_pedido=p.numero_pedido,
                        loja_id=p.loja_id,
                        total=p.total,
                    )
                    for p in pedidos_rows
                ],
                comprador_email=pedidos_rows[0].comprador_email if pedidos_rows else None,
                redirect_url=redirect_url,
                transaction_uuid=str(tx.uuid) if tx else None,
                checkout_type=(pr_dict or {}).get("checkout_type"),
                qr_code=(pr_dict or {}).get("qr_code"),
                copy_paste_code=(pr_dict or {}).get("copy_paste_code"),
                pix=_marketplace_pix_from_stored_response(pr_dict),
            )

    pedidos_criados: List[PedidoMarketplace] = []
    try:
        for lid in loja_ids:
            loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == lid).first()
            if not loja:
                raise HTTPException(status_code=404, detail=f"Loja {lid} não encontrada")
            sub = _pedido_body_from_unificado(body, lid, grupos[lid])
            comp, created = resolve_comprador_para_loja(db, loja, sub, consumidor)
            p = criar_pedido_marketplace_checkout(db, loja, sub, comp, created)
            pedidos_criados.append(p)

        session_uuid = str(uuid.uuid4())
        mc = MarketplaceCheckoutSession(
            uuid=session_uuid,
            idempotency_key=idem_key,
            status="pendente",
            total_agregado=0,
        )
        db.add(mc)
        db.flush()
        for i, p in enumerate(pedidos_criados):
            db.add(
                MarketplaceCheckoutSessionPedido(
                    session_id=mc.id,
                    pedido_id=p.id,
                    sort_order=i,
                )
            )
        db.flush()

        base_url = _public_base_url_for_checkout(request)
        anchor = pedidos_criados[0]
        back_success = (
            f"{base_url}/loja/pagamento/sucesso?session={session_uuid}&pedido={anchor.id}" if base_url else None
        )
        back_cancel = (
            f"{base_url}/loja/pagamento/cancelado?session={session_uuid}&pedido={anchor.id}" if base_url else None
        )
        out = create_checkout_for_session(
            db,
            mc.id,
            session_uuid,
            [p.id for p in pedidos_criados],
            getattr(body, "payment_method", "pix") or "pix",
            back_url_success=back_success,
            back_url_cancel=back_cancel,
            base_url=base_url,
        )
        return PedidoCheckoutUnificadoResponse(
            session_uuid=session_uuid,
            pedidos=[
                PedidoResumoUnificado(
                    id=p.id,
                    numero_pedido=p.numero_pedido,
                    loja_id=p.loja_id,
                    total=p.total,
                )
                for p in pedidos_criados
            ],
            comprador_email=pedidos_criados[0].comprador_email,
            redirect_url=out.get("redirect_url"),
            transaction_uuid=out.get("transaction_uuid"),
            checkout_type=out.get("checkout_type"),
            qr_code=out.get("qr_code"),
            copy_paste_code=out.get("copy_paste_code"),
            pix=out.get("pix"),
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        from ...core.logging import log_error

        log_error(f"checkout_unificado erro: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao finalizar checkout unificado. Tente novamente em instantes.")


# --- API pública de regras de frete da loja ---
@router.get("/{loja_id}/frete")
def get_frete_loja(
    loja_id: int,
    cidade: Optional[str] = None,
    uf: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Retorna regras de frete da loja (público, sem auth).
    Quando `cidade` e `uf` informados, verifica área de abrangência e retorna taxa da cidade."""
    loja = db.query(LojaMarketplace).filter(
        LojaMarketplace.id == loja_id,
        LojaMarketplace.status == "ativo",
    ).first()
    if not loja:
        raise HTTPException(status_code=404, detail="Loja não encontrada ou inativa")

    resp = {
        "formato_frete": getattr(loja, "formato_frete", None) or "sem_frete",
        "tipo_entrega": loja.tipo_entrega or "retirada",
        "taxa_entrega_fixa": float(loja.taxa_entrega_fixa) if loja.taxa_entrega_fixa else None,
        "entrega_gratis_apos": float(loja.entrega_gratis_apos) if loja.entrega_gratis_apos else None,
        "raio_entrega_km": loja.raio_entrega_km,
    }

    if cidade and uf:
        from sqlalchemy import func
        area = db.query(LojaAreaEntrega).filter(
            LojaAreaEntrega.loja_id == loja_id,
            func.lower(LojaAreaEntrega.cidade) == cidade.strip().lower(),
            func.upper(LojaAreaEntrega.uf) == uf.strip().upper(),
            LojaAreaEntrega.ativo == True,
        ).first()
        if area:
            resp["entrega_disponivel"] = True
            resp["taxa_entrega_cidade"] = float(area.taxa_entrega)
            resp["prazo_dias"] = area.prazo_dias
        else:
            has_any_area = db.query(LojaAreaEntrega).filter(
                LojaAreaEntrega.loja_id == loja_id,
                LojaAreaEntrega.ativo == True,
            ).first()
            if has_any_area:
                resp["entrega_disponivel"] = False
                resp["mensagem"] = "Não entregamos nessa localidade"
            else:
                resp["entrega_disponivel"] = True
                resp["taxa_entrega_cidade"] = float(loja.taxa_entrega_fixa) if loja.taxa_entrega_fixa else 0
                resp["prazo_dias"] = None

    return resp


# --- Nova tentativa de pagamento (gateway) ---
class NovaTentativaPagamentoBody(BaseModel):
    payment_method: str = "pix"
    numero_pedido: Optional[str] = None
    email: Optional[str] = None


@router.post("/pedidos/{pedido_id}/nova-tentativa-pagamento")
async def nova_tentativa_pagamento(
    pedido_id: int,
    request: Request,
    body: NovaTentativaPagamentoBody,
    db: Session = Depends(get_db),
    _: None = Depends(check_loja_nova_tentativa_rate_limit),
):
    """Gera novo link de checkout para o pedido (nova tentativa). Exige prova de posse: consumidor logado OU numero_pedido+email."""
    from app.services.payments.checkout_marketplace_service import create_retry_checkout_for_pedido

    from ...core.logging import log_error

    consumidor = await get_current_consumidor_optional(request, db)
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if consumidor:
        if pedido.comprador_id != consumidor.id:
            raise HTTPException(status_code=403, detail="Este pedido não pertence à sua conta")
    else:
        numero = (body.numero_pedido or "").strip()
        email_norm = (body.email or "").strip().lower()
        if not numero or not email_norm:
            raise HTTPException(
                status_code=400,
                detail="Para pedidos sem login, informe numero_pedido e email do comprador",
            )
        if pedido.numero_pedido != numero:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")
        if (pedido.comprador_email or "").strip().lower() != email_norm:
            raise HTTPException(status_code=403, detail="E-mail não confere com o pedido")

    base_url = _public_base_url_for_checkout(request)
    back_success = f"{base_url}/loja/pagamento/sucesso?pedido={pedido_id}" if base_url else None
    back_cancel = f"{base_url}/loja/pagamento/cancelado?pedido={pedido_id}" if base_url else None
    try:
        out = create_retry_checkout_for_pedido(
            db, pedido_id, body.payment_method,
            back_url_success=back_success,
            back_url_cancel=back_cancel,
            base_url=base_url,
        )
        return out
    except ValueError as e:
        log_error(f"nova_tentativa_pagamento ValueError: {e} (pedido_id={pedido_id})", exc_info=True)
        raise HTTPException(status_code=400, detail="Não foi possível gerar o link de pagamento. Verifique os dados do pedido.")
    except Exception as e:
        log_error(f"nova_tentativa_pagamento erro: {e} (pedido_id={pedido_id})", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao gerar link de pagamento. Tente novamente em instantes.")


@router.post("/checkout-sessao/{session_uuid}/nova-tentativa-pagamento")
async def nova_tentativa_pagamento_sessao(
    session_uuid: str,
    request: Request,
    body: NovaTentativaPagamentoBody,
    db: Session = Depends(get_db),
    _: None = Depends(check_loja_nova_tentativa_rate_limit),
):
    """Nova tentativa de pagamento para checkout unificado (todos os pedidos da sessão, um pagamento)."""
    from app.services.payments.checkout_marketplace_service import create_retry_checkout_for_session

    from ...core.logging import log_error

    su = (session_uuid or "").strip()
    if not su:
        raise HTTPException(status_code=400, detail="Sessão inválida")
    mc = db.query(MarketplaceCheckoutSession).filter(MarketplaceCheckoutSession.uuid == su).first()
    if not mc:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    links = (
        db.query(MarketplaceCheckoutSessionPedido)
        .filter(MarketplaceCheckoutSessionPedido.session_id == mc.id)
        .order_by(MarketplaceCheckoutSessionPedido.sort_order.asc())
        .all()
    )
    if not links:
        raise HTTPException(status_code=404, detail="Sessão sem pedidos")
    pedido_ids = [link.pedido_id for link in links]
    pedidos_rows = db.query(PedidoMarketplace).filter(PedidoMarketplace.id.in_(pedido_ids)).all()
    by_id = {p.id: p for p in pedidos_rows}
    ordered = [by_id[pid] for pid in pedido_ids if pid in by_id]
    if len(ordered) != len(pedido_ids):
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    anchor = ordered[0]
    consumidor = await get_current_consumidor_optional(request, db)
    if consumidor:
        for p in ordered:
            if p.comprador_id is None or p.comprador_id != consumidor.id:
                raise HTTPException(status_code=403, detail="Esta sessão não pertence à sua conta")
    else:
        numero = (body.numero_pedido or "").strip()
        email_norm = (body.email or "").strip().lower()
        if not numero or not email_norm:
            raise HTTPException(
                status_code=400,
                detail="Para checkout sem login, informe numero_pedido e email do comprador",
            )
        if anchor.numero_pedido != numero:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        if (anchor.comprador_email or "").strip().lower() != email_norm:
            raise HTTPException(status_code=403, detail="E-mail não confere com o pedido")
        em0 = (anchor.comprador_email or "").strip().lower()
        for p in ordered:
            if (p.comprador_email or "").strip().lower() != em0:
                raise HTTPException(status_code=403, detail="Dados da sessão inconsistentes")

    base_url = _public_base_url_for_checkout(request)
    back_success = f"{base_url}/loja/pagamento/sucesso?session={su}&pedido={anchor.id}" if base_url else None
    back_cancel = f"{base_url}/loja/pagamento/cancelado?session={su}&pedido={anchor.id}" if base_url else None
    try:
        return create_retry_checkout_for_session(
            db,
            su,
            body.payment_method,
            back_url_success=back_success,
            back_url_cancel=back_cancel,
            base_url=base_url,
        )
    except ValueError as e:
        log_error(f"nova_tentativa_pagamento_sessao ValueError: {e} (session={su})", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e) or "Não foi possível gerar o link de pagamento.")
    except Exception as e:
        log_error(f"nova_tentativa_pagamento_sessao erro: {e} (session={su})", exc_info=True)
        raise HTTPException(status_code=502, detail="Falha ao gerar link de pagamento. Tente novamente em instantes.")


# --- Completar cadastro (GUEST → REGISTERED) ---
@router.post("/completar-cadastro", response_model=ConsumidorResponse)
async def completar_cadastro(
    body: CompletarCadastroBody,
    db: Session = Depends(get_db),
    _: None = Depends(check_loja_cadastro_rate_limit),
):
    """Define senha e ativa conta para consumidor GUEST que comprou com email+numero_pedido."""
    email_norm = body.email.strip().lower()
    numero = (body.numero_pedido or "").strip()
    if not numero or not body.senha or len(body.senha) < 6:
        raise HTTPException(status_code=400, detail="Número do pedido e senha (mín. 6 caracteres) são obrigatórios")
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.numero_pedido == numero).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    if (pedido.comprador_email or "").strip().lower() != email_norm:
        raise HTTPException(status_code=403, detail="E-mail não confere com o pedido")
    consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.id == pedido.comprador_id).first()
    if not consumidor or consumidor.tipo_consumidor != "GUEST":
        raise HTTPException(status_code=400, detail="Este pedido não está vinculado a um cadastro para completar")
    consumidor.senha_hash = AuthConfig.get_password_hash(body.senha)
    consumidor.tipo_consumidor = "REGISTERED"
    consumidor.status_cadastro = "COMPLETO"
    if consumidor.tenant_id:
        emit_integration_event(
            db,
            tenant_id=consumidor.tenant_id,
            event_name="consumer.registered",
            entity_type="consumer",
            entity_id=consumidor.id,
            payload={
                "id": consumidor.id,
                "email": consumidor.email,
                "tipo_consumidor": consumidor.tipo_consumidor,
                "updated_at": consumidor.updated_at.isoformat() if getattr(consumidor, "updated_at", None) else None,
            },
        )
    db.commit()
    db.refresh(consumidor)
    return ConsumidorResponse.model_validate(consumidor)


# --- Consulta do pedido do consumidor logado (sem e-mail) ---
@router.get("/pedido/meu", response_model=PedidoConsultarResponse)
async def meu_pedido(
    numero_pedido: str = Query(..., description="Número do pedido"),
    db: Session = Depends(get_db),
    consumidor: ConsumidorMarketplace = Depends(get_current_consumidor),
):
    """Retorna o pedido do consumidor logado (acompanhamento na própria conta)."""
    numero = (numero_pedido or "").strip()
    if not numero:
        raise HTTPException(status_code=400, detail="Número do pedido é obrigatório")
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.numero_pedido == numero).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    if pedido.comprador_id != consumidor.id:
        raise HTTPException(status_code=403, detail="Este pedido não pertence à sua conta")
    itens = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == pedido.id).all()
    itens_resumo = [
        {
            "nome": getattr(item, "nome_produto_snapshot", None) or "",
            "quantidade": item.quantidade,
            "preco_unitario": float(item.preco_unitario or 0),
            "subtotal": float(item.preco_total or 0),
        }
        for item in itens
    ]
    from app.models import PedidoStatusEvento
    eventos = (
        db.query(PedidoStatusEvento)
        .filter(PedidoStatusEvento.pedido_id == pedido.id)
        .order_by(PedidoStatusEvento.created_at.asc())
        .all()
    )
    timeline = [
        {
            "tipo_evento": ev.tipo_evento,
            "status_codigo": ev.status_codigo,
            "status_label": ev.status_label,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev in eventos
    ]
    return PedidoConsultarResponse(
        id=pedido.id,
        numero_pedido=pedido.numero_pedido,
        status_pedido=pedido.status_pedido or "",
        status_pagamento=pedido.status_pagamento or "",
        status_entrega=getattr(pedido, "status_entrega", "") or "pendente",
        total=pedido.total,
        created_at=pedido.created_at,
        itens=itens_resumo,
        timeline=timeline,
    )


# --- Consulta pública de pedido (numero_pedido + email) ---
@router.get("/pedido/consultar", response_model=PedidoConsultarResponse)
async def consultar_pedido(
    numero_pedido: str = Query(..., description="Número do pedido"),
    email: str = Query(..., description="E-mail do comprador"),
    db: Session = Depends(get_db),
    _: None = Depends(check_loja_pedido_consultar_rate_limit),
):
    """Retorna resumo do pedido para acompanhamento (público, desde que email confira)."""
    numero = (numero_pedido or "").strip()
    email_norm = (email or "").strip().lower()
    if not numero or not email_norm:
        raise HTTPException(status_code=400, detail="Número do pedido e e-mail são obrigatórios")
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.numero_pedido == numero).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    if (pedido.comprador_email or "").strip().lower() != email_norm:
        raise HTTPException(status_code=403, detail="E-mail não confere com o pedido")
    itens = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == pedido.id).all()
    itens_resumo = [
        {
            "nome": getattr(item, "nome_produto_snapshot", None) or "",
            "quantidade": item.quantidade,
            "preco_unitario": float(item.preco_unitario or 0),
            "subtotal": float(item.preco_total or 0),
        }
        for item in itens
    ]
    from app.models import PedidoStatusEvento
    eventos = (
        db.query(PedidoStatusEvento)
        .filter(PedidoStatusEvento.pedido_id == pedido.id)
        .order_by(PedidoStatusEvento.created_at.asc())
        .all()
    )
    timeline = [
        {
            "tipo_evento": ev.tipo_evento,
            "status_codigo": ev.status_codigo,
            "status_label": ev.status_label,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev in eventos
    ]
    return PedidoConsultarResponse(
        id=pedido.id,
        numero_pedido=pedido.numero_pedido,
        status_pedido=pedido.status_pedido or "",
        status_pagamento=pedido.status_pagamento or "",
        status_entrega=getattr(pedido, "status_entrega", "") or "pendente",
        total=pedido.total,
        created_at=pedido.created_at,
        itens=itens_resumo,
        timeline=timeline,
    )


# ═══════════════════════════════════════════════════════════════
# Mobile endpoints (Sprint 1 — Fase 0)
# ═══════════════════════════════════════════════════════════════

@router.post("/refresh-token", response_model=RefreshTokenResponse)
async def loja_refresh_token(
    body: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """Renova access + refresh token (rotação segura)."""
    new_access, new_refresh, _ = rotate_consumidor_refresh_token(
        db, body.refresh_token
    )
    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}


@router.post("/auth/social/apple")
async def loja_apple_sign_in(
    body: AppleSignInRequest,
    db: Session = Depends(get_db),
):
    """Sign In with Apple — verifica id_token, cria/associa consumidor, retorna JWT + refresh."""
    apple_client_id = settings.LOJA_OAUTH_APPLE_SERVICE_ID or settings.LOJA_OAUTH_APPLE_CLIENT_ID
    if not apple_client_id:
        raise HTTPException(status_code=501, detail="Apple Sign-In não configurado")

    try:
        apple_payload = await verify_apple_id_token(body.id_token, apple_client_id)
    except (ValueError, Exception):
        raise HTTPException(
            status_code=401,
            detail={"detail": "Verificação Apple falhou", "code": AUTH_APPLE_VERIFICATION_FAILED},
        )

    apple_sub = apple_payload.get("sub")
    apple_email = apple_payload.get("email")
    if not apple_sub or not apple_email:
        raise HTTPException(status_code=401, detail="id_token Apple sem sub/email")

    social = (
        db.query(ConsumidorSocialIdentity)
        .filter(
            ConsumidorSocialIdentity.provider == "apple",
            ConsumidorSocialIdentity.provider_user_id == apple_sub,
        )
        .first()
    )
    if social:
        consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.id == social.consumidor_id).first()
        if not consumidor or not consumidor.ativo:
            raise HTTPException(status_code=403, detail="Conta desativada")
    else:
        email_lower = apple_email.strip().lower()
        consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.email == email_lower).first()
        if not consumidor:
            nome = body.nome or email_lower.split("@")[0]
            consumidor = ConsumidorMarketplace(
                email=email_lower,
                nome=nome,
                aceite_termos=True,
                ativo=True,
                email_verificado=True,
                origem_cadastro="app_mobile",
                canal_origem="apple",
                origem_social_provider="apple",
            )
            db.add(consumidor)
            db.flush()

        new_social = ConsumidorSocialIdentity(
            consumidor_id=consumidor.id,
            provider="apple",
            provider_user_id=apple_sub,
            provider_email=apple_email,
        )
        db.add(new_social)
        db.commit()
        db.refresh(consumidor)

    access_token = create_consumidor_token(consumidor.id)
    refresh_raw, _ = create_consumidor_refresh_token(db, consumidor.id, device_info="apple_sign_in")

    return {
        "access_token": access_token,
        "refresh_token": refresh_raw,
        "token_type": "bearer",
        "consumidor": {
            "id": consumidor.id,
            "nome": consumidor.nome,
            "email": consumidor.email,
        },
    }


@router.post("/push-token", response_model=PushTokenResponse, status_code=201)
async def loja_registrar_push_token(
    body: PushTokenCreate,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    """Registra ou atualiza push token FCM do dispositivo."""
    pt = registrar_push_token(
        db,
        consumidor_id=consumidor.id,
        token=body.token,
        plataforma=body.plataforma,
        device_id=body.device_id,
    )
    return pt


@router.delete("/push-token/{token}", status_code=204)
async def loja_remover_push_token(
    token: str,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    """Remove push token do dispositivo (logout ou desinstalação)."""
    removed = remover_push_token(db, consumidor.id, token)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail={"detail": "Push token não encontrado", "code": PUSH_TOKEN_NAO_ENCONTRADO},
        )


@router.get("/app-version/{plataforma}", response_model=AppVersionResponse)
async def loja_app_version(
    plataforma: str,
    db: Session = Depends(get_db),
):
    """Retorna versão mínima/recomendada do app (para force-update / soft-update)."""
    from ...models.app_versao_config import AppVersaoConfig
    config = db.query(AppVersaoConfig).filter(AppVersaoConfig.plataforma == plataforma.lower()).first()
    if not config:
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Plataforma '{plataforma}' não configurada", "code": APP_VERSAO_NAO_ENCONTRADA},
        )
    return config


# ─── Mobile: Parcelamento ───────────────────────────────────
@router.get("/parcelamento")
async def loja_parcelamento(
    valor: float = Query(..., gt=0),
):
    """Simula parcelas com/sem juros para um dado valor."""
    from ...services.parcelamento_service import simular_parcelas
    return simular_parcelas(Decimal(str(valor)))


# ─── Mobile: Upload de imagem (devolução/chat) ──────────────
@router.post("/upload")
async def loja_upload_imagem(
    request: Request,
    consumidor=Depends(get_current_consumidor),
):
    """Upload de imagem do consumidor (max 5MB, jpeg/png/webp). Retorna URL."""
    import os
    import uuid as _uuid
    content_type = request.headers.get("content-type", "")
    ALLOWED = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    ext = None
    for mime, extension in ALLOWED.items():
        if mime in content_type:
            ext = extension
            break
    if not ext:
        raise HTTPException(status_code=400, detail={"detail": "Tipo de arquivo inválido. Aceitos: jpeg, png, webp", "code": "UPLOAD_INVALID_TYPE"})

    body = await request.body()
    MAX_SIZE = 5 * 1024 * 1024
    if len(body) > MAX_SIZE:
        raise HTTPException(status_code=413, detail={"detail": "Arquivo excede 5MB", "code": "UPLOAD_SIZE_EXCEEDED"})

    upload_dir = os.path.join("uploads", "consumidor", str(consumidor.id))
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{_uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(body)

    url = f"/uploads/consumidor/{consumidor.id}/{filename}"
    return {"url": url, "filename": filename}
