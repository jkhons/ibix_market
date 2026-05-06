import asyncio
import datetime
import os
import re
import time
import uuid
from typing import Optional
from urllib.parse import urljoin, urlparse
from xml.sax.saxutils import escape

import anyio

# Importar para middlewares
from app.core.auth import AuthConfig
from app.core.config import settings

# Importar sistemas de segurança e logging
from app.core.logging import install_redact_token_filter, log_error, logger, setup_database_logging

# Importar middleware de autenticação
from app.core.middleware import check_auth_for_html
from app.core.rate_limiter import check_loja_public_page_rate_limit, get_client_ip, tenant_rate_limiter
from app.core.redis_cache import get_subscription_blocked_cached

# Importação centralizada de routers (RouterRegistry)
from app.core.routers import RouterRegistry, load_and_register_routers
from app.core.slug_utils import (
    SLUG_REGEX,
    first_non_empty,
    normalize_slug_or_404,
    parse_produto_slug_id,
    produto_slug_url,
    slugify,
)
from app.core.subscription_guard import _path_in_allowlist, check_subscription_redirect, is_subscription_blocked

# Importar configurações do banco
from app.database.connection import SessionLocal, engine, get_db
from app.models import *  # Importar todos os modelos
from app.models.usuario import Usuario
from app.utils.visitante import classificar_visitante
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import ClientDisconnect

ROUTER_SPECS = [
    ("app.api.v1.auth", "router", "auth"),
    ("app.api.v1.clientes", "router", "clientes"),
    ("app.api.v1.minha_equipe", "router", "minha_equipe"),
    ("app.api.v1.tipo_equipamento", "router", "tipo_equipamento"),
    ("app.api.v1.usuarios", "usuarios_router", "usuarios"),
    ("app.api.v1.roles", "router", "roles"),
    ("app.api.v1.permissoes", "router", "permissoes"),
    ("app.api.v1.configuracoes", "configuracoes_router", "configuracoes"),
    ("app.api.v1.email_cliente", "router", "email_cliente"),
    ("app.api.v1.whatsapp", "router", "whatsapp"),
    ("app.api.v1.templates_contratos", "router", "templates_contratos"),
    ("app.api.v1.help_center", "router", "help_center"),
    ("app.api.v1.landing", "router", "landing"),
    ("app.api.v1.notificacoes", "router", "notificacoes"),
    ("app.api.v1.dashboard_negocios", "router", "dashboard_negocios"),
    ("app.api.v1.vendas", "router", "vendas"),
    ("app.api.v1.orcamentos", "router", "orcamentos"),
    ("app.api.v1.pedidos", "router", "pedidos"),
    ("app.api.v1.ordens_servico", "router", "ordens_servico"),
    ("app.api.v1.empresa", "router", "empresa_fiscal"),
    ("app.api.v1.notas_fiscais", "router", "notas_fiscais"),
    ("app.api.v1.regras_fiscais_icms", "router", "regras_fiscais_icms"),
    ("app.api.v1.notas_servico", "router", "notas_servico"),
    ("app.api.v1.fiscal_relatorios", "router", "fiscal_relatorios"),
    ("app.api.v1.relatorios", "router", "relatorios"),
    ("app.api.v1.cupons_fiscais", "router", "cupons_fiscais"),
    ("app.api.v1.mdfe", "router", "mdfe"),
    ("app.api.v1.form_builder", "router", "form_builder"),
    ("app.api.v1.billing", "router", "billing"),
    ("app.api.v1.admin_billing", "router", "admin_billing"),
    ("app.api.v1.admin_audit_pagamentos", "router", "admin_audit_pagamentos"),
    ("app.api.v1.nfse", "router", "nfse"),
    ("app.api.v1.tenant_config", "router", "tenant_config"),
    ("app.api.v1.admin_dashboard", "router", "admin_dashboard"),
    ("app.api.webhooks_mercadopago", "router", "webhooks_mp"),
    ("app.api.webhooks_payments", "router", "webhooks_payments"),
    ("app.api.v1.plans", "router", "plans"),
    ("app.api.v1.portal", "router", "portal"),
    ("app.api.v1.caixas", "router", "caixas"),
    ("app.api.v1.aberturas_caixa", "router", "aberturas_caixa"),
    ("app.api.v1.produtos_cliente", "router", "produtos_cliente"),
    ("app.api.v1.google_custom_search", "router", "google_custom_search"),
    ("app.api.v1.admin_google_cse", "router", "admin_google_cse"),
    ("app.api.v1.material_categoria", "router", "material_categoria"),
    ("app.api.v1.tipo_material", "router", "tipo_material"),
    ("app.api.v1.movimentacoes_estoque", "router", "movimentacoes_estoque"),
    ("app.api.v1.fornecedores_cliente", "router", "fornecedores_cliente"),
    ("app.api.v1.produtos_fornecedor", "router", "produtos_fornecedor"),
    ("app.api.v1.nfe_entrada", "router", "nfe_entrada"),
    ("app.api.v1.onboarding", "router", "onboarding"),
    ("app.api.v1.venda_pagamentos", "router", "venda_pagamentos"),
    ("app.api.v1.movimentos_caixa", "router", "movimentos_caixa"),
    ("app.api.v1.payments", "router", "payments"),
    ("app.api.v1.payments_connect", "router", "payments_connect"),
    ("app.api.v1.repasses", "router", "repasses"),
    ("app.api.v1.senha_mestra", "router", "senha_mestra"),
    ("app.api.v1.precos_pdv", "router", "precos_pdv"),
    ("app.api.v1.contratos_comerciais", "router", "contratos_comerciais"),
    ("app.api.v1.codigos_desconto", "router", "codigos_desconto"),
    ("app.api.v1.precos_publico", "router", "precos_publico"),
    ("app.api.v1.admin_hierarquia", "router", "admin_hierarquia"),
    ("app.api.v1.marketplace", "router", "marketplace"),
    ("app.api.v1.loja", "router", "loja"),
    ("app.api.v1.loja_favoritos", "router", "loja_favoritos"),
    ("app.api.v1.loja_notificacoes", "router", "loja_notificacoes"),
    ("app.api.v1.loja_cupons", "router", "loja_cupons"),
    ("app.api.v1.loja_devolucao", "router", "loja_devolucao"),
    ("app.api.v1.loja_chat", "router", "loja_chat"),
    ("app.api.v1.loja_lgpd", "router", "loja_lgpd"),
    ("app.api.v1.loja_busca", "router", "loja_busca"),
    ("app.api.v1.ws_loja", "router", "ws_loja"),
    ("app.api.v1.marketing_vitrine", "router", "marketing_vitrine"),
    ("app.api.v1.integracao", "router", "integracao"),
    ("app.api.v1.entregador", "router", "entregador"),
    ("app.api.v1.logistica", "router", "logistica"),
    ("app.api.v1.influencers", "router", "influencers"),
]
load_and_register_routers(ROUTER_SPECS, log_error)

# Schema gerenciado por Alembic (alembic upgrade head).
# Nao usar Base.metadata.create_all: conflita com tabelas já criadas por migrations
# (ex.: certificado_peso_snapshot, certificado_equipamento_auxiliar_snapshot).

app = FastAPI(
    title="PDV Ibix",
    description="PDV Ibix - Sistema de vendas e gestão PDV (Ibix)",
    version="1.0.0",
    docs_url=None,        # ❌ Swagger DESABILITADO
    redoc_url=None,       # ❌ ReDoc DESABILITADO
    openapi_url=None      # ❌ OpenAPI DESABILITADO
)

# Redação de token em access log (não expor JWT em syslog/arquivos)
install_redact_token_filter()
# Log de banco (sqlalchemy.engine) em logs/database.log
setup_database_logging()
# Indicar onde estão os arquivos de log (login_falha e outros eventos em security.log / pdv_solumatica.log)
_log_dir = getattr(logger, "_log_dir", None)
if _log_dir:
    logger.info("Logs: %s (security.log, pdv_solumatica.log, errors.log). Para ver falhas de login: tail -f %s/security.log" % (_log_dir, _log_dir))

# CORS: em produção, exige CORS_ORIGINS explícito; wildcard só em dev.
_cors_origins = os.getenv("CORS_ORIGINS", "").strip()
_is_production = (settings.ENV or "").lower() == "production"
if _cors_origins:
    _origins_list = [o.strip() for o in _cors_origins.split(",") if o.strip()]
    _cors_allow_origins = _origins_list if _origins_list else ["https://www.ibix.com.br"]
elif _is_production:
    _cors_allow_origins = ["https://www.ibix.com.br", "https://ibix.com.br"]
    logger.warning("CORS_ORIGINS não definido em produção — usando domínios padrão Ibix")
else:
    _cors_allow_origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Requested-With"],
)

# X-Forwarded-Proto / X-Forwarded-For (nginx, Cloudflare): base_url e canonical corretos em HTTPS.
if os.getenv("TRUST_PROXY_HEADERS", "").strip().lower() in ("1", "true", "yes", "on"):
    try:
        from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

        app.add_middleware(ProxyHeadersMiddleware)
    except ImportError:
        logger.warning("TRUST_PROXY_HEADERS ativo mas ProxyHeadersMiddleware não disponível (uvicorn).")

# ============================================================================
# SWAGGER DESABILITADO - Middleware removido para melhor performance
# ============================================================================
# Para reativar, configure docs_url="/docs" no FastAPI() acima

# ============================================================================
# MIDDLEWARE REQUEST_ID + CORRELAÇÃO (E1.7/E5.3 - logs estruturados)
# ============================================================================


@app.middleware("http")
async def request_in_log_middleware(request: Request, call_next):
    """Correlação de request; sem log por requisição (evita ruído em multi-tenant)."""
    response = await call_next(request)
    return response


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Define request_id em toda requisição para correlação em logs (request_id, tenant_id, user_id)."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def api_request_log_middleware(request: Request, call_next):
    """Pass-through; access log do servidor já registra método, path e status."""
    response = await call_next(request)
    return response


# ============================================================================
# MIDDLEWARE - Captura desconexão do cliente (EndOfStream) para não logar traceback
# Executado primeiro (mais externo) para capturar exceções de qualquer camada interna
# ============================================================================
@app.middleware("http")
async def catch_client_disconnect(request: Request, call_next):
    """Desconexão do cliente: resposta vazia 499 (evita JSON no browser e falsos positivos por __cause__)."""
    try:
        return await call_next(request)
    except ClientDisconnect:
        logger.debug("Cliente desconectou (ClientDisconnect)")
        return Response(status_code=499, content=b"")
    except anyio.EndOfStream:
        logger.debug("Cliente desconectou (EndOfStream)")
        return Response(status_code=499, content=b"")
    except (ConnectionResetError, BrokenPipeError) as exc:
        logger.debug("Conexão fechada: %s", type(exc).__name__)
        return Response(status_code=499, content=b"")


# ============================================================================
# MIDDLEWARE ACCESS_LOG - Classificação de visitantes (HUMANO/BOT/CLOUD)
# Executa em thread separada para não bloquear o event loop
# ============================================================================
def _should_skip_access_log(path: str) -> bool:
    """Evita logar rotas que geram muito ruído (assets, API, health, metrics)."""
    skip_prefixes = ("/static/", "/api/", "/metrics", "/api/health", "/favicon")
    return any(path.startswith(p) for p in skip_prefixes)


# access_log via Celery: não bloqueia requisição; reativado por padrão (estável).
ACCESS_LOG_ENABLED = os.getenv("ACCESS_LOG_ENABLED", "true").lower() == "true"


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    """Registra acesso em access_log via Celery (classificação HUMANO/BOT/CLOUD)."""
    response = await call_next(request)
    if not ACCESS_LOG_ENABLED or _should_skip_access_log(request.url.path):
        return response
    try:
        from app.worker.tasks import log_access_task
        ip = get_client_ip(request)
        ua = request.headers.get("user-agent") or ""
        tipo = classificar_visitante(ip, ua)
        path = request.url.path[:512] if request.url.path else None
        log_access_task.delay(ip, ua, tipo, path)
    except Exception:
        pass
    return response

# ============================================================================
# MIDDLEWARE DE PERFORMANCE - Identificar requisições lentas
# ============================================================================

@app.middleware("http")
async def performance_logger(request: Request, call_next):
    """Medir tempo de requisições e identificar gargalos"""
    start_time = time.time()
    
    # Processar requisição
    response = await call_next(request)
    
    # Calcular tempo em milissegundos
    process_time = (time.time() - start_time) * 1000
    
    if not _is_production:
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    
    return response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Headers de segurança para sistema na internet (OWASP recommended headers)."""
    request.state.csp_nonce = ""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(self), payment=(self), usb=()"
    )
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    _csp_extra = os.getenv("CSP_EXTRA_SOURCES", "").strip()
    _csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://sdk.mercadopago.com https://www.googletagmanager.com https://www.google-analytics.com https://code.jquery.com https://maps.googleapis.com https://accounts.google.com https://www.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self' https://*.ibix.com.br https://cdn.jsdelivr.net https://api.mercadopago.com https://viacep.com.br https://www.google-analytics.com https://accounts.google.com https://oauth2.googleapis.com https://www.googleapis.com wss:; "
        "frame-src 'self' https://sdk.mercadopago.com https://accounts.google.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    if _csp_extra:
        _csp += "; " + _csp_extra
    response.headers["Content-Security-Policy"] = _csp
    return response


def _check_subscription_sync(request: Request):
    """Executa check em thread para não bloquear o event loop."""
    db = SessionLocal()
    try:
        return check_subscription_redirect(request, db)
    finally:
        db.close()


# Bypass do subscription guard em emergência (ex.: sistema travado por DB/Redis lento)
SUBSCRIPTION_GUARD_ENABLED = os.getenv("SUBSCRIPTION_GUARD_ENABLED", "true").lower() == "true"
# DIAG: logs detalhados de middleware (add_user, subscription_block). Em produção deixar false; usar true só para debug.
MIDDLEWARE_DIAG = os.getenv("MIDDLEWARE_DIAG", "false").lower() == "true"


@app.middleware("http")
async def subscription_block_redirect(request: Request, call_next):
    """Redireciona para /financeiro/assinatura quando assinatura está bloqueada (allowlist de rotas)."""
    path = request.url.path
    if _path_in_allowlist(path) or path.startswith("/static") or path.startswith("/api/"):
        return await call_next(request)
    if not getattr(request.state, "user_id", None):
        return await call_next(request)
    if not SUBSCRIPTION_GUARD_ENABLED:
        return await call_next(request)
    import asyncio
    if MIDDLEWARE_DIAG:
        logger.info(f"DIAG: subscription_block_redirect START {path}")
    try:
        loop = asyncio.get_running_loop()
        redirect_resp = await asyncio.wait_for(
            loop.run_in_executor(None, _check_subscription_sync, request),
            timeout=2.0,
        )
        if MIDDLEWARE_DIAG:
            logger.info(f"DIAG: subscription_block_redirect DONE {path}")
        if redirect_resp:
            return redirect_resp
    except asyncio.TimeoutError:
        if MIDDLEWARE_DIAG:
            logger.warning(f"DIAG: subscription_block_redirect TIMEOUT {path}")
        pass  # Se DB demorar, deixa passar (evita travamento)
    except Exception:
        pass  # Nunca bloquear a requisição por falha no guard
    if MIDDLEWARE_DIAG:
        logger.info(f"DIAG: subscription_block calling route {path}")
    response = await call_next(request)
    if MIDDLEWARE_DIAG:
        logger.info(f"DIAG: subscription_block route DONE {path}")
    return response


@app.middleware("http")
async def tenant_rate_limit_middleware(request: Request, call_next):
    """Rate limit por tenant em rotas /api/v1/ autenticadas. Quando tenant_id é None (ex.: Superadmin), não aplica limite por tenant."""
    if not request.url.path.startswith("/api/v1/"):
        return await call_next(request)
    # Vitrine pública/consumidor tem limitadores próprios no módulo loja; não deve consumir cota de tenant do PDV.
    if request.url.path.startswith("/api/v1/loja"):
        return await call_next(request)
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        return await call_next(request)
    try:
        from app.core.scope import resolve_tenant_pagador
        from app.database.connection import SessionLocal
        from sqlalchemy.orm import joinedload
        db = SessionLocal()
        try:
            user = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == user_id).first()
            if not user:
                return await call_next(request)
            tenant_id = resolve_tenant_pagador(db, user.id, user.role.nome if user.role else None)
            if tenant_id is not None:
                allowed, error_message = await asyncio.to_thread(tenant_rate_limiter.is_allowed, str(tenant_id))
                if not allowed:
                    log_error(f"Rate limit por tenant excedido tenant_id={tenant_id}: {error_message}")
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Limite de requisições excedido para esta organização. Tente novamente em breve.", "retry_after": 60},
                    )
        finally:
            db.close()
    except Exception:
        pass  # Em falha, deixa passar para não bloquear a requisição
    return await call_next(request)


@app.middleware("http")
async def add_user_to_request(request: Request, call_next):
    """Preenche request.state com user_payload, user_id e cliente_id (do JWT). cliente_id = estabelecimento/contexto, não tenant_id de billing. DEVE rodar ANTES de subscription_block."""
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    if not token:
        token = request.cookies.get("pdv_solumatica_token") or request.cookies.get("pdv_automscale_token")
    if token:
        try:
            if MIDDLEWARE_DIAG:
                logger.info("DIAG: add_user_to_request before verify_token")
            payload = AuthConfig.verify_token(token)
            if MIDDLEWARE_DIAG:
                logger.info("DIAG: add_user_to_request after verify_token")
            user_id = payload.get("sub")
            if user_id:
                request.state.user_id = int(user_id)
                request.state.user_payload = payload
            # cliente_id do JWT (estabelecimento/contexto), não o tenant_id de billing; usado para correlação em logs
            cid = payload.get("cliente_id")
            if cid is not None:
                request.state.cliente_id = int(cid) if isinstance(cid, (int, float)) else cid
        except Exception:
            pass
    response = await call_next(request)
    return response


# Handler global de exceções (Saas.md 1.3): em produção não expor stack trace
PRODUCTION_MODE = os.getenv("ENV", "").lower() == "production" or os.getenv("DEBUG", "false").lower() != "true"


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: StarletteHTTPException):
    """404 handler: HTML para browsers, JSON para API."""
    accept = request.headers.get("accept", "")
    if request.url.path.startswith("/api/") or "text/html" not in accept:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    return await _render_template_async("errors/404.html", {"request": request}, status_code=404)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Em produção retorna mensagem genérica; em desenvolvimento pode incluir detalhes."""
    if isinstance(exc, ClientDisconnect):
        logger.debug("Cliente desconectou (ClientDisconnect)")
        return Response(status_code=499, content=b"")
    if isinstance(exc, anyio.EndOfStream):
        logger.debug("Cliente desconectou (EndOfStream)")
        return Response(status_code=499, content=b"")
    if isinstance(exc, (ConnectionResetError, BrokenPipeError)):
        logger.debug("Conexão fechada: %s", type(exc).__name__)
        return Response(status_code=499, content=b"")
    rid = getattr(request.state, "request_id", None)
    # cliente_id do JWT (correlação); para tenant_id de billing seria necessário resolve_tenant_pagador no middleware
    cid = getattr(request.state, "cliente_id", None)
    tid = str(cid) if cid is not None else None
    uid = str(getattr(request.state, "user_id", None)) if getattr(request.state, "user_id", None) is not None else None
    log_error("Exceção não tratada", exc_info=exc, request_id=rid, tenant_id=tid, user_id=uid)
    if PRODUCTION_MODE:
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno do servidor. Tente novamente mais tarde."},
        )
    raise exc

# Versão dos estáticos do PDV: muda a cada restart para evitar cache em tablet
PDV_STATIC_VERSION = os.environ.get("PDV_STATIC_VERSION", str(int(time.time())))

# Configurar templates Jinja2
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["slugify"] = slugify

COOKIE_LOJA_CONSUMIDOR = "loja_consumidor_token"


async def _loja_consumidor_logado(request: Request) -> bool:
    """Retorna True se o request tiver cookie/token de consumidor válido (vitrine)."""
    token = request.cookies.get(COOKIE_LOJA_CONSUMIDOR) or (
        request.headers.get("Authorization") or ""
    ).replace("Bearer ", "").strip()
    if not token:
        return False
    try:
        payload = AuthConfig.verify_token(token)
        return payload.get("tipo") == "consumidor"
    except Exception:
        return False


def _loja_consumidor_id(request: Request) -> int | None:
    """Retorna o id do consumidor logado na vitrine, ou None (para chave de carrinho por usuário)."""
    token = request.cookies.get(COOKIE_LOJA_CONSUMIDOR) or (
        (request.headers.get("Authorization") or "").replace("Bearer ", "").strip()
    )
    if not token:
        return None
    try:
        payload = AuthConfig.verify_token(token)
        if payload.get("tipo") != "consumidor":
            return None
        cid = payload.get("sub")
        return int(cid) if cid else None
    except Exception:
        return None


def _loja_consumidor_nome(request: Request, db: Session) -> str | None:
    """Retorna o nome do consumidor logado na vitrine, ou None."""
    token = request.cookies.get(COOKIE_LOJA_CONSUMIDOR) or (
        request.headers.get("Authorization") or ""
    ).replace("Bearer ", "").strip()
    if not token:
        return None
    try:
        payload = AuthConfig.verify_token(token)
        if payload.get("tipo") != "consumidor":
            return None
        cid = payload.get("sub")
        if not cid:
            return None
        consumidor = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.id == int(cid)).first()
        return consumidor.nome if consumidor else None
    except Exception:
        return None


async def _render_template_async(name: str, context: dict, status_code: int = 200):
    """Renderiza template Jinja2 em thread para não bloquear o event loop (evita travamento em rotas HTML)."""
    def _do():
        tpl = templates.env.get_template(name)
        return tpl.render(context)
    html = await asyncio.to_thread(_do)
    return HTMLResponse(html, status_code=status_code)


# PWA desativado temporariamente
# @app.get("/sw-calibracao.js", response_class=FileResponse, include_in_schema=False)
# def serve_pwa_service_worker():
#     return FileResponse("app/static/sw-calibracao.js", media_type="application/javascript")


# Servir arquivos estáticos da aplicação
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Middleware personalizado para proteger arquivos PDF - OTIMIZADO
@app.middleware("http")
async def protect_pdf_files(request: Request, call_next):
    """Middleware para proteger arquivos PDF. Usa request.state.user_payload quando preenchido pelo middleware de auth."""
    path = request.url.path
    
    # ⚡ OTIMIZAÇÃO: Retornar rapidamente se não for PDF protegido
    if not (path.startswith("/static/docs/certificados_auxiliares/") and path.endswith(".pdf")):
        return await call_next(request)
    
    # É um PDF protegido - verificar autenticação (reutilizar payload já verificado se disponível)
    if getattr(request.state, "user_payload", None):
        return await call_next(request)
    token = request.cookies.get("pdv_solumatica_token")
    if not token:
        raise HTTPException(status_code=401, detail="Acesso negado - autenticação necessária")
    try:
        payload = AuthConfig.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Token inválido")
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")
    return await call_next(request)


def _legacy_seo_path_should_redirect(path: str) -> bool:
    """Rotas públicas que devem 301 do host legado para SEO_PUBLIC_BASE_URL (evita duplicata no Google)."""
    mode = (getattr(settings, "SEO_REDIRECT_LEGACY_PATH_MODE", None) or "public").strip().lower()
    if mode == "all":
        if path.startswith(("/api/", "/static/", "/dashboard", "/admin")):
            return False
        return True
    exact = frozenset(
        {
            "/",
            "/index.html",
            "/login",
            "/cadastro",
            "/cadastro-representante",
            "/cadastro-influencer",
            "/cadastro-influencer/sucesso",
            "/help-center",
            "/manual",
            "/representantes",
            "/termos-de-uso",
            "/politica-privacidade",
            "/politica-privacidade-marketplace",
        }
    )
    if path in exact:
        return True
    if path == "/loja" or path.startswith("/loja/"):
        return True
    if path.startswith("/categoria/"):
        return True
    if path.startswith("/sitemap") or path.startswith("/robots") or path.startswith("/merchant-feed"):
        return True
    return False


@app.middleware("http")
async def redirect_legacy_host_to_seo_canonical(request: Request, call_next):
    """301 de hosts legados para SEO_PUBLIC_BASE_URL (mesmo path e query), só em rotas públicas de SEO.
    Uso (oficial = ibix): SEO_PUBLIC_BASE_URL=https://www.ibix.com.br
         SEO_REDIRECT_LEGACY_HOSTS=www.solumatica.com.br,solumatica.com.br
    Opcional: SEO_REDIRECT_LEGACY_PATH_MODE=all (agressivo no host legado; evite se ainda houver /dashboard só lá).
    """
    if request.method not in ("GET", "HEAD"):
        return await call_next(request)
    path = request.url.path or "/"
    if path.startswith("/static/"):
        return await call_next(request)
    canonical = (getattr(settings, "SEO_PUBLIC_BASE_URL", None) or "").strip().rstrip("/")
    legacy_raw = os.getenv("SEO_REDIRECT_LEGACY_HOSTS", "").strip()
    if not canonical or not legacy_raw:
        return await call_next(request)
    if not _legacy_seo_path_should_redirect(path):
        return await call_next(request)
    legacy_hosts = {h.strip().lower() for h in legacy_raw.split(",") if h.strip()}
    host = (request.headers.get("host") or "").split(":")[0].lower()
    if host not in legacy_hosts:
        return await call_next(request)
    canon_host = (urlparse(canonical).hostname or "").lower()
    if host == canon_host:
        return await call_next(request)
    target = f"{canonical}{path}"
    q = request.url.query
    if q:
        target = f"{target}?{q}"
    return RedirectResponse(url=target, status_code=301)


# Incluir routers registrados (prefix/tags por nome)
ROUTER_INCLUDE = [
    ("auth", "/api/v1", None),
    ("clientes", "/api/v1", None),
    ("minha_equipe", "/api/v1", None),
    ("tipo_equipamento", "/api/v1", None),
    ("usuarios", "/api/v1", None),
    ("roles", "/api/v1", None),
    ("permissoes", "/api/v1", None),
    ("configuracoes", "/api/v1", None),
    ("email_cliente", "/api/v1", None),
    ("whatsapp", "/api/v1", None),
    ("templates_contratos", "/api/v1/templates-contratos", ["Templates de Contratos"]),
    ("help_center", None, None),
    ("landing", "/api/v1", None),
    ("notificacoes", None, None),
    ("dashboard_negocios", "/api/v1", None),
    ("vendas", "/api/v1", ["Vendas"]),
    ("orcamentos", "/api/v1", None),
    ("pedidos", "/api/v1", None),
    ("ordens_servico", "/api/v1", ["Ordens de Serviço"]),
    ("empresa_fiscal", "/api/v1", None),
    ("notas_fiscais", "/api/v1", None),
    ("regras_fiscais_icms", "/api/v1", None),
    ("notas_servico", "/api/v1", None),
    ("fiscal_relatorios", "/api/v1", None),
    ("relatorios", "/api/v1", None),
    ("cupons_fiscais", "/api/v1", None),
    ("mdfe", "/api/v1", None),
    ("form_builder", "/api/v1", None),
    ("billing", "/api/v1", None),
    ("admin_billing", "/api/v1", None),
    ("admin_audit_pagamentos", "/api/v1", None),
    ("nfse", "/api/v1", None),
    ("tenant_config", "/api/v1", None),
    ("admin_dashboard", "/api/v1", None),
    ("webhooks_mp", "/api/webhooks", None),
    ("webhooks_payments", "/api/webhooks", None),
    ("plans", "/api/v1", None),
    ("portal", "/api/v1", None),
    ("caixas", "/api/v1", None),
    ("aberturas_caixa", "/api/v1", None),
    ("produtos_cliente", "/api/v1", None),
    ("google_custom_search", "/api/v1", None),
    ("admin_google_cse", "/api/v1", None),
    ("material_categoria", "/api/v1", None),
    ("tipo_material", "/api/v1", None),
    ("movimentacoes_estoque", "/api/v1", None),
    ("fornecedores_cliente", "/api/v1", None),
    ("produtos_fornecedor", "/api/v1", None),
    ("nfe_entrada", "/api/v1", None),
    ("onboarding", "/api/v1", None),
    ("venda_pagamentos", "/api/v1", None),
    ("movimentos_caixa", "/api/v1", None),
    ("payments", "/api/v1", None),
    ("payments_connect", "/api/v1", None),
    ("repasses", "/api/v1", None),
    ("senha_mestra", "/api/v1", None),
    ("precos_pdv", "/api/v1", None),
    ("contratos_comerciais", "/api/v1", None),
    ("codigos_desconto", "/api/v1", None),
    ("precos_publico", "/api/v1", None),
    ("admin_hierarquia", "/api/v1", None),
    ("marketplace", "/api/v1", None),
    ("loja", "/api/v1", None),
    ("loja_favoritos", "/api/v1", None),
    ("loja_notificacoes", "/api/v1", None),
    ("loja_cupons", "/api/v1", None),
    ("loja_devolucao", "/api/v1", None),
    ("loja_chat", "/api/v1", None),
    ("loja_lgpd", "/api/v1", None),
    ("loja_busca", "/api/v1", None),
    ("ws_loja", None, None),
    ("marketing_vitrine", "/api/v1", None),
    ("integracao", "/api", None),
    ("entregador", "/api/v1", None),
    ("logistica", "/api/v1", None),
]
for name, prefix, tags in ROUTER_INCLUDE:
    router = RouterRegistry.get(name)
    if router:
        kwargs = {}
        if prefix:
            kwargs["prefix"] = prefix
        if tags:
            kwargs["tags"] = tags
        app.include_router(router, **kwargs)

# ============================================================================
# PROMETHEUS METRICS (observabilidade E7.1)
# ============================================================================
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
except Exception as e:
    log_error("Prometheus Instrumentator não carregado", exc_info=e)

# ============================================================================
# ROTAS HTML DA APLICAÇÃO
# ============================================================================

def get_template_context(request: Request, db: Session):
    """Obtém contexto comum para templates incluindo permissões do usuário.
    Reutiliza request.state (user_id, user_payload, user_permissions, user) para evitar queries duplicadas na mesma requisição."""
    context = {"request": request, "user_is_cliente": False, "subscription_blocked": False, "csp_nonce": getattr(request.state, "csp_nonce", "")}
    try:
        user_id = getattr(request.state, "user_id", None)
        payload = getattr(request.state, "user_payload", None)
        if not payload or not user_id:
            token = request.cookies.get("pdv_solumatica_token")
            if token:
                payload = AuthConfig.verify_token(token)
                user_id = payload.get("sub")
                if user_id:
                    user_id = int(user_id)
                    request.state.user_id = user_id
                    request.state.user_payload = payload
        if not user_id:
            return context
        if not payload:
            payload = {}
        from app.core.middleware import get_user_with_permissions
        user = getattr(request.state, "user", None)
        if hasattr(request.state, "user_permissions"):
            user_permissions = request.state.user_permissions
            if user is None:
                user = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == user_id).first()
                request.state.user = user
        else:
            user, user_permissions = get_user_with_permissions(user_id, db)
            request.state.user_permissions = user_permissions
            request.state.user = user
        context["user_permissions"] = user_permissions
        if user:
            context["user_id"] = user.id
            context["user_name"] = user.nome
            context["user_email"] = user.email
            if user.role:
                context["user_role"] = user.role.nome
            context["user_can_edit_fiscal"] = not (user.role and user.role.nome == "Contador")
            context["subscription_blocked"] = get_subscription_blocked_cached(
                user.id, lambda: is_subscription_blocked(db, user)
            )
            area_cliente = db.query(AreaCliente).filter(
                AreaCliente.usuario_id == user.id,
                AreaCliente.ativo == True
            ).first()
            context["user_is_cliente"] = (
                bool(payload.get("cliente_id"))
                or area_cliente is not None
                or payload.get("role") == "Cliente"
            )
    except Exception as e:
        log_error(f"Erro ao obter contexto do template: {e}", exc_info=e)
    return context


async def get_template_context_async(request: Request, db: Session):
    """Executa get_template_context em thread pool para não bloquear o event loop (Redis/DB síncronos)."""
    return await asyncio.to_thread(get_template_context, request, db)


async def _response_403(request: Request, db: Session, error_message: str):
    """Retorna TemplateResponse da página 403 com contexto completo (sidebar, user_permissions, etc.)."""
    ctx = await get_template_context_async(request, db)
    ctx["error_message"] = error_message
    return await _render_template_async("errors/403.html", ctx, status_code=403)


async def check_html_any_module_permission(request: Request, db: Session, modulos: list, error_message: str):
    """Verifica se o usuário tem permissão para ao menos um dos módulos. Usa get_user_permissions (sem query extra)."""
    try:
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            token = request.cookies.get("pdv_solumatica_token")
            if not token:
                return RedirectResponse(url="/login", status_code=302)
            payload = AuthConfig.verify_token(token)
            user_id = payload.get("sub")
            if not user_id:
                return RedirectResponse(url="/login", status_code=302)
            user_id = int(user_id)
        from app.core.middleware import get_user_permissions
        if hasattr(request.state, "user_permissions"):
            perms = request.state.user_permissions
        else:
            perms = await asyncio.to_thread(get_user_permissions, user_id, db)
            request.state.user_permissions = perms
        if not any(m in perms for m in modulos):
            return await _response_403(request, db, error_message)
        return None
    except Exception:
        return RedirectResponse(url="/login", status_code=302)


async def check_html_module_permission(request: Request, db: Session, modulo: str, error_message: str):
    """Verifica se o usuário tem permissão para o módulo (role_permissoes). Retorna Response 403 ou None.
    Reutiliza request.state.user_payload e request.state.user_permissions quando disponíveis."""
    try:
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            token = request.cookies.get("pdv_solumatica_token")
            if not token:
                return RedirectResponse(url="/login", status_code=302)
            payload = AuthConfig.verify_token(token)
            user_id = payload.get("sub")
            if not user_id:
                return RedirectResponse(url="/login", status_code=302)
            user_id = int(user_id)
        from app.core.middleware import get_user_permissions
        if hasattr(request.state, "user_permissions"):
            perms = request.state.user_permissions
        else:
            perms = await asyncio.to_thread(get_user_permissions, user_id, db)
            request.state.user_permissions = perms
        if modulo not in perms:
            return await _response_403(request, db, error_message)
        return None
    except Exception:
        return RedirectResponse(url="/login", status_code=302)


async def check_html_permission(request: Request, db: Session, permission_name: str, error_message: str):
    """Verifica se o usuário tem a permissão específica (nome completo). Retorna Response 403 ou None."""
    try:
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            token = request.cookies.get("pdv_solumatica_token")
            if not token:
                return RedirectResponse(url="/login", status_code=302)
            payload = AuthConfig.verify_token(token)
            user_id = payload.get("sub")
            if not user_id:
                return RedirectResponse(url="/login", status_code=302)
            user_id = int(user_id)
        from app.core.middleware import get_user_permissions
        if hasattr(request.state, "user_permissions"):
            perms = request.state.user_permissions
        else:
            perms = await asyncio.to_thread(get_user_permissions, user_id, db)
            request.state.user_permissions = perms
        if permission_name not in perms:
            return await _response_403(request, db, error_message)
        return None
    except Exception:
        return RedirectResponse(url="/login", status_code=302)


def _landing_base_url(request: Request) -> str:
    """URL base pública para canonical, OG e sitemap.
    Ordem: SEO_PUBLIC_BASE_URL (domínio oficial indexável) → host da requisição → APP_URL.
    Defina SEO_PUBLIC_BASE_URL em produção com o domínio oficial (ex.: https://www.ibix.com.br) quando APP_URL ou
    o host visto pelo proxy não coincidir com o que você submete no Search Console, evitando canônicos conflitantes.
    """
    explicit = (getattr(settings, "SEO_PUBLIC_BASE_URL", None) or "").strip().rstrip("/")
    if explicit:
        return explicit
    base = str(request.base_url).rstrip("/") if request.base_url else ""
    if base:
        return base
    return (settings.APP_URL or "").rstrip("/") if settings.APP_URL else ""


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    """Página inicial: vitrine (loja). Sempre exibida; usuário PDV logado vê link Painel no header."""
    await check_loja_public_page_rate_limit(request)
    return await _render_template_async("loja/index.html", await _loja_context(request, db=db))


@app.get("/index.html", response_class=HTMLResponse)
async def index_html(request: Request, db: Session = Depends(get_db)):
    """Página index.html: mesmo que / — vitrine sempre exibida."""
    await check_loja_public_page_rate_limit(request)
    return await _render_template_async("loja/index.html", await _loja_context(request, db=db))


@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt(request: Request):
    """robots.txt para indexação: permite páginas públicas e aponta para o sitemap."""
    base = _landing_base_url(request)
    sitemap_url = f"{base}/sitemap.xml" if base else ""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Allow: /login",
        "Allow: /cadastro",
        "Allow: /cadastro-representante",
        "Allow: /cadastro-influencer",
        "Allow: /termos-de-uso",
        "Allow: /politica-privacidade",
        "Allow: /politica-privacidade-marketplace",
        "Allow: /representantes",
        "Allow: /help-center",
        "Allow: /manual",
        "Disallow: /dashboard",
        "Disallow: /api/",
        "Disallow: /admin/",
    ]
    if sitemap_url:
        lines.append(f"Sitemap: {sitemap_url}")
    return "\n".join(lines)


# HEAD explícito: sem isto, FastAPI responde 405 em HEAD. Validadores e o Google
# Search Console podem testar HEAD antes do GET e marcar "Não foi possível buscar o sitemap".
@app.head("/robots.txt", include_in_schema=False)
async def robots_txt_head():
    return Response(content=b"", media_type="text/plain; charset=utf-8")


@app.head("/sitemap.xml", include_in_schema=False)
async def sitemap_index_xml_head():
    return Response(content=b"", media_type="application/xml")


@app.head("/sitemap-pages.xml", include_in_schema=False)
async def sitemap_pages_xml_head():
    return Response(content=b"", media_type="application/xml")


@app.head("/sitemap-produtos.xml", include_in_schema=False)
async def sitemap_produtos_xml_head():
    return Response(content=b"", media_type="application/xml")


@app.head("/sitemap-categorias.xml", include_in_schema=False)
async def sitemap_categorias_xml_head():
    return Response(content=b"", media_type="application/xml")


@app.head("/sitemap-lojas.xml", include_in_schema=False)
async def sitemap_lojas_xml_head():
    return Response(content=b"", media_type="application/xml")


def _sitemap_base(request: Request) -> str:
    base = _landing_base_url(request)
    if not base:
        base = str(request.base_url).rstrip("/") if request.base_url else ""
    return base


def _absolute_public_url(base: str, raw: Optional[str]) -> str:
    """Converte path de imagem (ex.: uploads/produtos/...) em URL absoluta. Igual à vitrine: /static/ + relativo."""
    if not raw or not isinstance(raw, str):
        return ""
    u = raw.strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    path = u if u.startswith("/") else f"/static/{u}"
    return f"{base.rstrip('/')}{path}"


def _build_urlset(entries: list[tuple], xmlns_extra: str = "") -> str:
    urls = "".join(
        f"  <url><loc>{loc}</loc><priority>{pri}</priority><changefreq>{chf}</changefreq></url>\n"
        for loc, pri, chf in entries
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"{xmlns_extra}>\n{urls}</urlset>'


def _urlset_entries_min_one(entries: list[tuple], base: str) -> list[tuple]:
    """Google Search Console rejeita urlset sem nenhum <url>. Se não houver dados, usa a vitrine."""
    if entries:
        return entries
    return [(f"{base}/loja", "0.3", "weekly")]


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_index_xml(request: Request):
    """Sitemap index apontando para sub-sitemaps separados por tipo."""
    base = _sitemap_base(request)
    sitemaps = [
        f"{base}/sitemap-pages.xml",
        f"{base}/sitemap-produtos.xml",
        f"{base}/sitemap-categorias.xml",
        f"{base}/sitemap-lojas.xml",
    ]
    entries = "".join(f"  <sitemap><loc>{s}</loc></sitemap>\n" for s in sitemaps)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}</sitemapindex>'
    return Response(content=xml, media_type="application/xml")


@app.get("/sitemap-pages.xml", include_in_schema=False)
async def sitemap_pages_xml(request: Request):
    """Sitemap de paginas estaticas publicas."""
    base = _sitemap_base(request)
    entries = [
        (f"{base}/", "1.0", "weekly"),
        (f"{base}/loja", "0.9", "weekly"),
        (f"{base}/login", "0.6", "monthly"),
        (f"{base}/cadastro", "0.8", "monthly"),
        (f"{base}/cadastro-representante", "0.7", "monthly"),
        (f"{base}/cadastro-influencer", "0.7", "monthly"),
        (f"{base}/termos-de-uso", "0.4", "yearly"),
        (f"{base}/politica-privacidade", "0.4", "yearly"),
        (f"{base}/politica-privacidade-marketplace", "0.4", "yearly"),
        (f"{base}/representantes", "0.6", "monthly"),
        (f"{base}/help-center", "0.5", "monthly"),
        (f"{base}/manual", "0.5", "monthly"),
    ]
    return Response(content=_build_urlset(entries), media_type="application/xml")


@app.get("/sitemap-produtos.xml", include_in_schema=False)
async def sitemap_produtos_xml(request: Request, db: Session = Depends(get_db)):
    """Sitemap de produtos publicados com URL amigavel e image sitemap."""
    base = _sitemap_base(request)
    entries: list[str] = []
    try:
        anuncios = db.query(AnuncioPlataforma).filter(AnuncioPlataforma.status == "publicado").limit(5000).all()
        import json as _json
        for a in anuncios:
            loc = f"{base}{produto_slug_url(a.titulo, a.id)}"
            lastmod = ""
            if hasattr(a, "updated_at") and a.updated_at:
                lastmod = f"<lastmod>{a.updated_at.strftime('%Y-%m-%d')}</lastmod>"
            imgs_xml = ""
            try:
                imgs = _json.loads(a.imagens) if a.imagens else []
                if not isinstance(imgs, list):
                    imgs = []
                for img_url in imgs[:5]:
                    abs_img = _absolute_public_url(base, str(img_url) if img_url else "")
                    if abs_img:
                        imgs_xml += (
                            f"<image:image><image:loc>{escape(abs_img)}</image:loc>"
                            f"<image:title>{escape(a.titulo or '')}</image:title></image:image>"
                        )
            except Exception:
                pass
            entries.append(f"  <url><loc>{loc}</loc>{lastmod}<priority>0.7</priority><changefreq>weekly</changefreq>{imgs_xml}</url>")
    except Exception as e:
        log_error("sitemap_produtos_xml: anúncios publicados", exc_info=e)
    if not entries:
        entries.append(
            f"  <url><loc>{base}/loja</loc><priority>0.5</priority><changefreq>weekly</changefreq></url>"
        )
    urls = "\n".join(entries)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n{urls}\n</urlset>'
    return Response(content=xml, media_type="application/xml")


@app.get("/sitemap-categorias.xml", include_in_schema=False)
async def sitemap_categorias_xml(request: Request, db: Session = Depends(get_db)):
    """Sitemap de categorias da plataforma e categorias locais."""
    base = _sitemap_base(request)
    entries = []
    try:
        categorias = db.query(CategoriaPlataforma).filter(CategoriaPlataforma.ativa == True).all()
        for cat in categorias:
            if cat.slug:
                entries.append((f"{base}/loja/categoria/{cat.slug}", "0.6", "weekly"))
    except Exception as e:
        log_error("sitemap_categorias_xml: categorias plataforma", exc_info=e)
    try:
        from sqlalchemy import func
        category_slugs = (
            db.query(LojaMarketplace.slug_categoria_cidade)
            .filter(
                LojaMarketplace.status == "ativo",
                LojaMarketplace.slug_categoria_cidade.isnot(None),
                func.length(func.trim(LojaMarketplace.slug_categoria_cidade)) > 0,
            )
            .distinct()
            .all()
        )
        for row in category_slugs:
            try:
                slug = normalize_slug_or_404(row[0])
                entries.append((f"{base}/categoria/{slug}", "0.8", "daily"))
            except Exception:
                continue
    except Exception as e:
        log_error("sitemap_categorias_xml: categorias locais", exc_info=e)
    return Response(
        content=_build_urlset(_urlset_entries_min_one(entries, base)),
        media_type="application/xml",
    )


@app.get("/sitemap-lojas.xml", include_in_schema=False)
async def sitemap_lojas_xml(request: Request, db: Session = Depends(get_db)):
    """Sitemap de lojas ativas no marketplace."""
    base = _sitemap_base(request)
    entries = []
    try:
        from sqlalchemy import func
        lojas = db.query(LojaMarketplace).filter(
            LojaMarketplace.status == "ativo",
            LojaMarketplace.slug.isnot(None),
            func.length(func.trim(LojaMarketplace.slug)) > 0,
        ).all()
        for loja in lojas:
            try:
                slug_norm = _normalize_public_loja_slug(loja.slug)
                entries.append((f"{base}/{slug_norm}", "0.8", "daily"))
            except HTTPException:
                continue
    except Exception as e:
        log_error("sitemap_lojas_xml: lojas ativas", exc_info=e)
    return Response(
        content=_build_urlset(_urlset_entries_min_one(entries, base)),
        media_type="application/xml",
    )


@app.get("/merchant-feed.xml", include_in_schema=False)
async def merchant_feed_xml(request: Request, db: Session = Depends(get_db)):
    """Google Merchant Center product feed (RSS 2.0 / XML) com atributos completos."""
    import json as _json
    base = _sitemap_base(request)
    items: list[str] = []
    try:
        anuncios = (
            db.query(AnuncioPlataforma)
            .options(
                joinedload(AnuncioPlataforma.produto_cliente),
                joinedload(AnuncioPlataforma.categoria),
                joinedload(AnuncioPlataforma.loja),
            )
            .filter(AnuncioPlataforma.status == "publicado")
            .limit(5000)
            .all()
        )
        for a in anuncios:
            pc = a.produto_cliente
            cat = a.categoria
            link = f"{base}{produto_slug_url(a.titulo, a.id)}"
            titulo_feed = a.titulo or ""
            if pc and pc.fabricante:
                titulo_feed = f"{pc.fabricante} {titulo_feed}"
            descricao = (a.descricao or "")[:5000].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            titulo_xml = (titulo_feed or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            imgs = []
            try:
                imgs = _json.loads(a.imagens) if a.imagens else []
                if not isinstance(imgs, list):
                    imgs = []
            except Exception:
                pass
            img_link = _absolute_public_url(base, str(imgs[0]) if imgs else "")
            additional_imgs = ""
            for extra_img in imgs[1:10]:
                au = _absolute_public_url(base, str(extra_img) if extra_img else "")
                if au:
                    additional_imgs += f"<g:additional_image_link>{escape(au)}</g:additional_image_link>"
            preco = float(a.preco_promocional or a.preco_original or 0)
            preco_original = float(a.preco_original or 0)
            preco_xml = f"<g:price>{preco:.2f} BRL</g:price>"
            if a.preco_promocional and float(a.preco_promocional) > 0 and preco_original > float(a.preco_promocional):
                preco_xml = f"<g:price>{preco_original:.2f} BRL</g:price><g:sale_price>{preco:.2f} BRL</g:sale_price>"
            availability = "in_stock" if a.estoque_atual and float(a.estoque_atual) > 0 else "in_stock"
            sku = (pc.codigo if pc else "") or str(a.id)
            brand = (pc.fabricante if pc else "") or "Ibix"
            category_name = (cat.nome if cat else "") or ""
            condition = "new"
            img_link_xml = f"<g:image_link>{escape(img_link)}</g:image_link>" if img_link else ""
            items.append(
                f"<item>"
                f"<g:id>{a.id}</g:id>"
                f"<g:title>{titulo_xml}</g:title>"
                f"<g:description>{descricao}</g:description>"
                f"<g:link>{escape(link)}</g:link>"
                f"{img_link_xml}"
                f"{additional_imgs}"
                f"{preco_xml}"
                f"<g:availability>{availability}</g:availability>"
                f"<g:condition>{condition}</g:condition>"
                f"<g:brand>{brand}</g:brand>"
                f"<g:mpn>{sku}</g:mpn>"
                f'{f"<g:product_type>{category_name}</g:product_type>" if category_name else ""}'
                f"</item>"
            )
    except Exception as e:
        log_error("merchant_feed_xml: erro ao gerar feed", exc_info=e)
    items_xml = "\n".join(items)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n'
        "<channel>\n"
        "<title>Ibix Marketplace</title>\n"
        f"<link>{base}/loja</link>\n"
        "<description>Produtos do Ibix Marketplace</description>\n"
        f"{items_xml}\n"
        "</channel>\n"
        "</rss>"
    )
    return Response(content=xml, media_type="application/xml")


@app.head("/merchant-feed.xml", include_in_schema=False)
async def merchant_feed_xml_head():
    return Response(content=b"", media_type="application/xml")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard principal do sistema. Token válido = não redirecionar para login; só exige permissão/dados do usuário."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    try:
        context = await get_template_context_async(request, db)
    except Exception as e:
        log_error("Erro ao obter contexto do dashboard", exc_info=e)
        context = {}
    # Se o contexto não trouxe user_id (ex.: falha ao carregar user/perms), tentar uma vez carregar usuário para não deslogar quem tem token válido
    if not context.get("user_id") and user_id:
        try:
            user = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == user_id).first()
            if user:
                from app.core.middleware import get_user_with_permissions
                _, user_permissions = get_user_with_permissions(user_id, db)
                request.state.user = user
                request.state.user_permissions = user_permissions
                context["user_id"] = user.id
                context["user_name"] = user.nome
                context["user_email"] = user.email
                context["user_permissions"] = user_permissions
                if user.role:
                    context["user_role"] = user.role.nome
                context["user_can_edit_fiscal"] = not (user.role and user.role.nome == "Contador")
                context["subscription_blocked"] = get_subscription_blocked_cached(
                    user.id, lambda: is_subscription_blocked(db, user)
                )
        except Exception as e2:
            log_error("Erro ao recuperar usuário no dashboard", exc_info=e2)
    if not context.get("user_id"):
        return RedirectResponse(url="/login", status_code=302)
    user_role = context.get("user_role")
    user_permissions = context.get("user_permissions") or []
    if user_role == "Subcliente":
        return RedirectResponse(url="/portal", status_code=302)
    if user_role != "Superadministrador" and "dashboard" not in user_permissions:
        return await _response_403(request, db, "Você não tem permissão para acessar o dashboard")
    # Dashboard oficial: Resumo financeiro (meu_negocio). Dashboard de certificados removido (sistema antigo).
    return await _render_template_async("meu_negocio/dashboard.html", context)

# Rotas de autenticação
@app.get("/login", response_class=HTMLResponse)
async def login(request: Request, db: Session = Depends(get_db)):
    """Página de login (mesmo padrão visual da vitrine: base loja, logo e header)."""
    ctx = await _loja_context(request, db=db)
    return await _render_template_async("auth/login.html", ctx)

@app.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    """Página de registro"""
    return await _render_template_async("auth/register.html", {"request": request})

@app.get("/cadastro", response_class=HTMLResponse)
async def cadastro_publico(request: Request):
    """Página de cadastro público (empresa + Cliente Administrador) — Saas.md Fase 6."""
    return await _render_template_async("auth/register_public.html", {"request": request})


@app.get("/auth/esqueci-senha", response_class=HTMLResponse)
async def auth_esqueci_senha(request: Request):
    """Página Esqueci minha senha (PDV)."""
    return await _render_template_async("auth/esqueci_senha.html", {"request": request})


@app.get("/auth/redefinir-senha", response_class=HTMLResponse)
async def auth_redefinir_senha(request: Request, token: Optional[str] = None):
    """Página Redefinir senha (PDV) com token na URL."""
    context = {"request": request, "token": token or ""}
    return await _render_template_async("auth/redefinir_senha.html", context)


@app.get("/cadastro-representante", response_class=HTMLResponse)
async def cadastro_representante(request: Request):
    """Página de cadastro público do Representante (Administrador) — mesmo formato do cadastro CA."""
    return await _render_template_async("auth/register_representante.html", {"request": request})


@app.get("/cadastro-influencer", response_class=HTMLResponse)
async def cadastro_influencer(request: Request):
    """Página de cadastro público do Influencer."""
    return await _render_template_async("auth/register_influencer.html", {"request": request})


@app.get("/cadastro-influencer/sucesso", response_class=HTMLResponse)
async def cadastro_influencer_sucesso(request: Request):
    """Página de sucesso pós-cadastro do Influencer."""
    return await _render_template_async("auth/register_influencer_sucesso.html", {"request": request})


@app.get("/i/{codigo_rastreio}")
async def influencer_redirect(codigo_rastreio: str, db: Session = Depends(get_db)):
    """Redirect de link rastreável de influencer — incrementa clique e redireciona."""
    from app.models.influencer_link import InfluencerLink
    from app.models.influencer_metrica import InfluencerMetrica
    lnk = db.query(InfluencerLink).filter(
        InfluencerLink.codigo_rastreio == codigo_rastreio,
        InfluencerLink.ativo == True,
    ).first()
    if not lnk:
        return RedirectResponse(url="/", status_code=302)
    metrica = db.query(InfluencerMetrica).filter(
        InfluencerMetrica.divulgador_id == lnk.divulgador_id,
        InfluencerMetrica.campanha_id == lnk.campanha_id,
    ).first()
    if metrica:
        metrica.cliques = (metrica.cliques or 0) + 1
    else:
        metrica = InfluencerMetrica(
            campanha_id=lnk.campanha_id,
            divulgador_id=lnk.divulgador_id,
            cliques=1,
        )
        db.add(metrica)
    db.commit()
    return RedirectResponse(url=lnk.url_destino, status_code=302)


@app.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request, db: Session = Depends(get_db)):
    """Página de alteração de senha"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    context = await get_template_context_async(request, db)
    return await _render_template_async("auth/change_password.html", context)

@app.get("/logout", response_class=HTMLResponse)
async def logout_page(request: Request):
    """Página de logout - redireciona para login"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/login")

# Rotas de páginas
@app.get("/clientes", response_class=HTMLResponse)
async def clientes(request: Request, db: Session = Depends(get_db)):
    """Página de gestão de clientes"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    perm_check = await check_html_module_permission(request, db, "clientes", "Você não tem permissão para acessar clientes")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    return await _render_template_async("clientes/index.html", context)


@app.get("/planos", response_class=HTMLResponse)
async def planos(request: Request, db: Session = Depends(get_db)):
    """Página de planos e assinatura (SaaS). Acesso via permissão planos (role_permissoes)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "planos", "Você não tem permissão para acessar Planos.")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    context["GATEWAY_CHECKOUT_URL"] = os.getenv("GATEWAY_CHECKOUT_URL", "")
    return await _render_template_async("planos/index.html", context)


@app.get("/financeiro/assinatura", response_class=HTMLResponse)
async def financeiro_assinatura(request: Request, db: Session = Depends(get_db)):
    """Página de assinatura: status e botão Pagar agora. Acessível a CA/Subcliente (e quando bloqueado)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    context = await get_template_context_async(request, db)
    return await _render_template_async("financeiro/assinatura.html", context)


@app.get("/billing/success")
def billing_success():
    """Retorno Checkout Pro (sucesso): redireciona para assinatura."""
    return RedirectResponse(url="/financeiro/assinatura", status_code=302)


@app.get("/billing/failure")
def billing_failure():
    """Retorno Checkout Pro (falha): redireciona para assinatura."""
    return RedirectResponse(url="/financeiro/assinatura", status_code=302)


@app.get("/billing/pending")
def billing_pending():
    """Retorno Checkout Pro (pendente): redireciona para assinatura."""
    return RedirectResponse(url="/financeiro/assinatura", status_code=302)


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Dashboard Admin: Super Admin vê visão global; Administrador vê CAs e participação."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role:
            return await _response_403(request, db, "Acesso restrito a Superadministrador ou Administrador.")
        role_nome = user.role.nome
        if role_nome not in ("Superadministrador", "Administrador"):
            return await _response_403(request, db, "Acesso restrito a Superadministrador ou Administrador.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    if role_nome == "Superadministrador":
        return await _render_template_async("admin/dashboard_super_admin.html", context)
    return await _render_template_async("admin/dashboard_administrador.html", context)


@app.get("/admin/billing/tenants", response_class=HTMLResponse)
async def admin_billing_tenants(request: Request, db: Session = Depends(get_db)):
    """Lista de tenants (billing) - apenas Superadministrador."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Superadministrador":
            return await _response_403(request, db, "Acesso restrito a Superadministrador (Billing Admin).")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("admin/billing_tenants.html", context)


@app.get("/admin/integracoes/google-custom-search", response_class=HTMLResponse)
async def admin_google_cse_page(request: Request, db: Session = Depends(get_db)):
    """Google Custom Search — credenciais e cotas por tenant. Apenas Superadministrador."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Superadministrador":
            return await _response_403(request, db, "Acesso restrito a Superadministrador.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("admin/google_cse.html", context)


@app.get("/admin/email", response_class=HTMLResponse)
async def admin_email(request: Request, db: Session = Depends(get_db)):
    """Configuração de e-mail (SMTP) - apenas Superadministrador."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Superadministrador":
            return await _response_403(request, db, "Acesso restrito a Superadministrador.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("admin/email.html", context)


@app.get("/admin/marketplace-seo-lojas", response_class=HTMLResponse)
async def admin_marketplace_seo_lojas(request: Request, db: Session = Depends(get_db)):
    """SEO avançado das lojas da vitrine — apenas Superadministrador."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Superadministrador":
            return await _response_403(request, db, "Acesso restrito a Superadministrador.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("admin/marketplace_seo_lojas.html", context)


@app.get("/admin/marketing-vitrine", response_class=HTMLResponse)
async def admin_marketing_vitrine(request: Request, db: Session = Depends(get_db)):
    """Marketing da vitrine (home) — config global e cards; apenas Superadministrador."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Superadministrador":
            return await _response_403(request, db, "Acesso restrito a Superadministrador.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("admin/marketing_vitrine.html", context)


@app.get("/admin/billing/tenant/{tenant_id:int}", response_class=HTMLResponse)
async def admin_billing_tenant_detail(request: Request, tenant_id: int, db: Session = Depends(get_db)):
    """Detalhe do tenant (billing) - apenas Superadministrador."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Superadministrador":
            return await _response_403(request, db, "Acesso restrito a Superadministrador (Billing Admin).")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    context["tenant_id"] = tenant_id
    return await _render_template_async("admin/billing_tenant_detail.html", context)


@app.get("/admin/billing/config", response_class=HTMLResponse)
async def admin_billing_config(request: Request, db: Session = Depends(get_db)):
    """Configuração billing (MP, APP_URL) - apenas Superadministrador."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Superadministrador":
            return await _response_403(request, db, "Acesso restrito a Superadministrador (Billing Admin).")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("admin/billing_config.html", context)


@app.get("/admin/billing/preco", response_class=HTMLResponse)
async def admin_billing_preco(request: Request, db: Session = Depends(get_db)):
    """Valor mensal e descontos (Super Admin)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Superadministrador":
            return await _response_403(request, db, "Acesso restrito a Superadministrador (Billing Admin).")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("admin/billing_preco.html", context)


@app.get("/admin/billing/precos-pdv", response_class=HTMLResponse)
async def admin_precos_pdv(request: Request, db: Session = Depends(get_db)):
    """Preços de licença PDV (Super Admin)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Superadministrador":
            return await _response_403(request, db, "Acesso restrito a Superadministrador.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("admin/precos_pdv.html", context)


@app.get("/admin/influencers", response_class=HTMLResponse)
async def admin_influencers(request: Request, db: Session = Depends(get_db)):
    """Painel de Influencers e Marketing (Super Admin)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Superadministrador":
            return await _response_403(request, db, "Acesso restrito a Superadministrador.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("admin/influencers.html", context)


@app.get("/admin/billing/codigos-desconto", response_class=HTMLResponse)
async def admin_codigos_desconto(request: Request, db: Session = Depends(get_db)):
    """Códigos de desconto e divulgadores (Super Admin / Admin)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome not in ("Superadministrador", "Administrador"):
            return await _response_403(request, db, "Acesso restrito a Superadministrador ou Administrador.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    role_admin = db.query(Role).filter(Role.nome == "Administrador").first()
    context["usuarios_administradores"] = (
        db.query(Usuario).filter(Usuario.role_id == role_admin.id).order_by(Usuario.nome).all()
        if role_admin else []
    )
    return await _render_template_async("admin/codigos_desconto.html", context)


@app.get("/admin/hierarquia", response_class=HTMLResponse)
async def admin_hierarquia_page(request: Request, db: Session = Depends(get_db)):
    """Hierarquia do sistema - apenas Superadministrador."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Superadministrador":
            return await _response_403(request, db, "Acesso restrito a Superadministrador.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("admin/hierarquia.html", context)


@app.get("/fiscal/empresa", response_class=HTMLResponse)
async def fiscal_empresa(request: Request, db: Session = Depends(get_db)):
    """Página de gestão de empresa fiscal"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    # Verificar permissões específicas para empresa fiscal
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        
        if not user or not user.role:
            return RedirectResponse(url="/login", status_code=302)
        
        has_permission = (user.role.nome == "Superadministrador") or db.query(Permissao).join(
            RolePermissao, RolePermissao.permissao_id == Permissao.id
        ).filter(
            RolePermissao.role_id == user.role_id,
            Permissao.nome == 'fiscal.empresa',
            Permissao.ativo == True
        ).first()
        
        if not has_permission:
            return await _response_403(request, db, "Você não tem permissão para acessar empresa fiscal")
            
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("fiscal/empresa.html", context)


def _fiscal_nfse_has_permission(db, user):
    """Verifica permissão fiscal (fiscal.empresa) para páginas NFS-e."""
    if not user or not user.role:
        return False
    if user.role.nome == "Superadministrador":
        return True
    return db.query(Permissao).join(
        RolePermissao, RolePermissao.permissao_id == Permissao.id
    ).filter(
        RolePermissao.role_id == user.role_id,
        Permissao.nome == "fiscal.empresa",
        Permissao.ativo == True
    ).first() is not None


@app.get("/fiscal/nfse-config", response_class=HTMLResponse)
async def fiscal_nfse_config(request: Request, db: Session = Depends(get_db)):
    """Configuração NFS-e do CA: empresa emissora e cliente tomador padrão; assistente IBGE."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        if not _fiscal_nfse_has_permission(db, user):
            return await _response_403(request, db, "Você não tem permissão para configurar NFS-e.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("fiscal/nfse_config.html", context)


@app.get("/fiscal/nfse-pendencias", response_class=HTMLResponse)
async def fiscal_nfse_pendencias(request: Request, db: Session = Depends(get_db)):
    """Tela de pendências NFS-e (QUEUED/REJECTED) com botão Tentar novamente."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user:
            return RedirectResponse(url="/login", status_code=302)
        if not _fiscal_nfse_has_permission(db, user):
            return await _response_403(request, db, "Você não tem permissão para acessar pendências NFS-e.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("fiscal/nfse_pendencias.html", context)


@app.get("/fiscal/notas-fiscais", response_class=HTMLResponse)
async def fiscal_notas_fiscais(request: Request, db: Session = Depends(get_db)):
    """Página de consulta de notas fiscais"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    # Verificar permissões específicas para notas fiscais
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        
        if not user or not user.role:
            return RedirectResponse(url="/login", status_code=302)
        
        # Verificar permissão fiscal (usar fiscal.empresa como base, ou criar permissão específica)
        has_permission = (user.role.nome == "Superadministrador") or db.query(Permissao).join(
            RolePermissao, RolePermissao.permissao_id == Permissao.id
        ).filter(
            RolePermissao.role_id == user.role_id,
            Permissao.modulo.in_(['fiscal.empresa', 'fiscal.notas-fiscais']),
            Permissao.ativo == True
        ).first()
        
        if not has_permission:
            return await _response_403(request, db, "Você não tem permissão para acessar notas fiscais")
            
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("fiscal/notas_fiscais.html", context)


@app.get("/fiscal/regras-fiscais-icms", response_class=HTMLResponse)
async def fiscal_regras_fiscais_icms(request: Request, db: Session = Depends(get_db)):
    """Página de cadastro de regras fiscais ICMS (motor tributário)"""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role:
            return RedirectResponse(url="/login", status_code=302)
        has_permission = (user.role.nome == "Superadministrador") or db.query(Permissao).join(
            RolePermissao, RolePermissao.permissao_id == Permissao.id
        ).filter(
            RolePermissao.role_id == user.role_id,
            Permissao.modulo.in_(['fiscal.empresa', 'fiscal.notas-fiscais']),
            Permissao.ativo == True
        ).first()
        if not has_permission:
            return await _response_403(request, db, "Você não tem permissão para acessar Regras Fiscais ICMS")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("fiscal/regras_fiscais_icms.html", context)


@app.get("/fiscal/area-contador", response_class=HTMLResponse)
async def fiscal_area_contador(request: Request, db: Session = Depends(get_db)):
    """Dashboard fiscal e listagem de documentos (área do contador). Exige fiscal:visualizar_documentos."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role:
            return RedirectResponse(url="/login", status_code=302)
        has_perm = (user.role.nome == "Superadministrador") or db.query(Permissao).join(
            RolePermissao, RolePermissao.permissao_id == Permissao.id
        ).filter(
            RolePermissao.role_id == user.role_id,
            Permissao.nome == "fiscal:visualizar_documentos",
            Permissao.ativo == True
        ).first()
        if not has_perm:
            return await _response_403(request, db, "Você não tem permissão para acessar a Área do Contador")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("fiscal/area_contador.html", context)


# Rota duplicada removida - usando a rota com verificação de permissões abaixo

# ========== Portal Subcliente (rotas /portal/*) ==========
async def _portal_require_subcliente(request: Request, db: Session):
    """Redireciona para /login se não autenticado; retorna 403 se não for Subcliente. Retorna (response_or_none, context)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check, None
    context = await get_template_context_async(request, db)
    user_role = context.get("user_role")
    if user_role != "Subcliente":
        return await _response_403(request, db, "Acesso restrito ao Portal do Cliente (Subcliente)."), None
    return None, context

@app.get("/portal", response_class=HTMLResponse)
async def portal_dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard do Portal Subcliente"""
    auth_check, context = await _portal_require_subcliente(request, db)
    if auth_check:
        return auth_check
    return await _render_template_async("portal/dashboard.html", context)

@app.get("/portal/historico", response_class=HTMLResponse)
async def portal_historico(request: Request, db: Session = Depends(get_db)):
    """Histórico / Agenda (Portal Subcliente)"""
    auth_check, context = await _portal_require_subcliente(request, db)
    if auth_check:
        return auth_check
    return await _render_template_async("portal/historico.html", context)

@app.get("/portal/downloads", response_class=HTMLResponse)
async def portal_downloads(request: Request, db: Session = Depends(get_db)):
    """Downloads (Portal Subcliente)"""
    auth_check, context = await _portal_require_subcliente(request, db)
    if auth_check:
        return auth_check
    return await _render_template_async("portal/downloads.html", context)

@app.get("/portal/minha-conta", response_class=HTMLResponse)
async def portal_minha_conta(request: Request, db: Session = Depends(get_db)):
    """Minha Conta (Portal Subcliente)"""
    auth_check, context = await _portal_require_subcliente(request, db)
    if auth_check:
        return auth_check
    return await _render_template_async("portal/minha_conta.html", context)


@app.get("/portal/ordens-servico", response_class=HTMLResponse)
async def portal_ordens_servico(request: Request, db: Session = Depends(get_db)):
    """Ordens de serviço (Portal Cliente Final)"""
    auth_check, context = await _portal_require_subcliente(request, db)
    if auth_check:
        return auth_check
    return await _render_template_async("portal/ordens_servico.html", context)


@app.get("/portal/notas-fiscais", response_class=HTMLResponse)
async def portal_notas_fiscais(request: Request, db: Session = Depends(get_db)):
    """Notas fiscais (Portal Cliente Final)"""
    auth_check, context = await _portal_require_subcliente(request, db)
    if auth_check:
        return auth_check
    return await _render_template_async("portal/notas_fiscais.html", context)


@app.get("/roles", response_class=HTMLResponse)
async def roles_page(request: Request, db: Session = Depends(get_db)):
    """Página de gestão de roles RBAC — exige usuarios:gerenciar_roles"""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    from app.models import Permissao, RolePermissao
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role:
            return RedirectResponse(url="/login", status_code=302)
        # Apenas Superadministrador pode acessar a página de roles (Administrador não)
        if user.role.nome != "Superadministrador":
            return await _response_403(request, db, "Gerenciamento de funções e permissões é restrito ao Superadministrador.")
        has_permission = (user.role.nome == "Superadministrador") or db.query(Permissao).join(
            RolePermissao, RolePermissao.permissao_id == Permissao.id
        ).filter(
            RolePermissao.role_id == user.role_id,
            Permissao.nome == "usuarios:gerenciar_roles",
            Permissao.ativo == True
        ).first()
        if not has_permission:
            return await _response_403(request, db, "Você não tem permissão para gerenciar funções e permissões (usuarios:gerenciar_roles)")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("roles/index.html", context)

def _redirect_with_cookie_set(url: str, token: str):
    """Redireciona para url e define cookie pdv_solumatica_token (evita perda de cookie em navegação)."""
    r = RedirectResponse(url=url, status_code=302)
    r.set_cookie(
        key="pdv_solumatica_token",
        value=token,
        httponly=False,
        secure=os.getenv("HTTPS", "false").lower() == "true",
        samesite="lax",
        max_age=28800,
        path="/",
    )
    return r


@app.get("/relatorios", response_class=HTMLResponse)
async def relatorios_page():
    """Redireciona para a página unificada de Relatórios (negócios)."""
    return RedirectResponse(url="/negocio/relatorios", status_code=302)


@app.get("/configuracoes", response_class=HTMLResponse)
async def configuracoes(request: Request, db: Session = Depends(get_db)):
    """Página de configurações do sistema. Apenas Superadministrador e Administrador. Um contexto, sem queries duplicadas."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        context = await get_template_context_async(request, db)
        if not context.get("user_id"):
            return RedirectResponse(url="/login", status_code=302)
        if context.get("user_role") == "Cliente Administrador":
            return await _response_403(request, db, "Acesso às configurações do sistema é restrito a Superadministrador e Administrador.")
        if "configuracoes" not in (context.get("user_permissions") or []):
            return await _response_403(request, db, "Você não tem permissão para acessar configurações")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    return await _render_template_async("configuracoes/index.html", context)

@app.get("/configuracoes/email/templates", response_class=HTMLResponse)
async def configuracoes_templates_email(request: Request, db: Session = Depends(get_db)):
    """Página de gerenciamento de templates de e-mail. Apenas Superadministrador e Administrador."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        context = await get_template_context_async(request, db)
        if not context.get("user_id"):
            return RedirectResponse(url="/login", status_code=302)
        if context.get("user_role") == "Cliente Administrador":
            return await _response_403(request, db, "Acesso às configurações é restrito a Superadministrador e Administrador.")
        if "configuracoes" not in (context.get("user_permissions") or []):
            return await _response_403(request, db, "Você não tem permissão para acessar esta página.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    return await _render_template_async("configuracoes/templates_email.html", context)

@app.get("/usuarios", response_class=HTMLResponse)
async def usuarios(request: Request, db: Session = Depends(get_db)):
    """Página de gerenciamento de usuários. Não acessível para Cliente Administrador (use Minha equipe)."""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    # Autorização por permissão granular: usuarios:visualizar; Cliente Administrador sem acesso
    from app.models import Permissao, RolePermissao
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        
        if not user or not user.role:
            return RedirectResponse(url="/login", status_code=302)
        if user.role.nome == "Cliente Administrador":
            return await _response_403(request, db, "Acesso à página de usuários não permitido para Cliente Administrador. Use Minha equipe para gerenciar sub-clientes e técnicos.")
        has_permission = (user.role.nome == "Superadministrador") or db.query(Permissao).join(
            RolePermissao, RolePermissao.permissao_id == Permissao.id
        ).filter(
            RolePermissao.role_id == user.role_id,
            Permissao.nome == "usuarios:visualizar",
            Permissao.ativo == True
        ).first()
        
        if not has_permission:
            return await _response_403(request, db, "Você não tem permissão para acessar o gerenciamento de usuários (usuarios:visualizar)")
            
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("usuarios/index.html", context)

@app.get("/minha-equipe", response_class=HTMLResponse)
async def minha_equipe(request: Request, db: Session = Depends(get_db)):
    """Página Minha equipe (Cliente Administrador) — sub-clientes e técnicos (Saas.md Fase 6.2)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    token = request.cookies.get("pdv_solumatica_token")
    if not token:
        return RedirectResponse(url="/login", status_code=302)
    payload = AuthConfig.verify_token(token)
    user_id = payload.get("sub")
    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    if not user or not user.role:
        return RedirectResponse(url="/login", status_code=302)
    if user.role.nome != "Cliente Administrador":
        return await _response_403(request, db, "Acesso restrito a Cliente Administrador.")
    context = await get_template_context_async(request, db)
    return await _render_template_async("minha_equipe/index.html", context)


@app.get("/email-cliente", response_class=HTMLResponse)
async def email_cliente(request: Request, db: Session = Depends(get_db)):
    """Página de configuração de e-mail por cliente. Acesso por permissão email_cliente (role_permissoes)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(
        request, db, "email_cliente", "Acesso restrito à configuração de e-mail por cliente."
    )
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    return await _render_template_async("configuracoes/email_cliente.html", context)


@app.get("/blank", response_class=HTMLResponse)
async def blank(request: Request, db: Session = Depends(get_db)):
    """Página em branco"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("pages/blank.html", context)

@app.get("/help-center", response_class=HTMLResponse)
async def help_center(request: Request, db: Session = Depends(get_db)):
    """Página de Central de Ajuda"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("pages/help-center.html", context)


@app.get("/politica-privacidade", response_class=HTMLResponse)
async def politica_privacidade(request: Request, db: Session = Depends(get_db)):
    """Página de Política de Privacidade"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("pages/politica-privacidade.html", context)

@app.get("/termos-de-uso", response_class=HTMLResponse)
async def termos_de_uso(request: Request, db: Session = Depends(get_db)):
    """Página de Termos de Uso"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("pages/termos-de-uso.html", context)


@app.get("/politica-privacidade-marketplace", response_class=HTMLResponse)
async def politica_privacidade_marketplace(request: Request):
    """Página pública de Política de Privacidade (marketplace/loja, LGPD). Não exige autenticação."""
    base_url = _landing_base_url(request)
    context = {"base_url": base_url or ""}
    return await _render_template_async("pages/politica-privacidade-marketplace.html", context)


@app.get("/como-funciona-vitrine", response_class=HTMLResponse)
async def como_funciona_vitrine(request: Request):
    """Página pública: vitrine, marketing da home, frete (loja x plataforma) e responsabilidade pela entrega."""
    base_url = _landing_base_url(request)
    context = {"base_url": base_url or ""}
    return await _render_template_async("pages/como-funciona-vitrine.html", context)


@app.get("/representantes", response_class=HTMLResponse)
async def representantes_revenda(request: Request):
    """Página pública Representantes, Influencers e Revenda."""
    base_url = _landing_base_url(request)
    context = {"base_url": base_url}
    return await _render_template_async("pages/representantes-revenda.html", context)


@app.get("/influencer/painel", response_class=HTMLResponse)
async def influencer_painel(request: Request, db: Session = Depends(get_db)):
    """Area do influencer — dashboard proprio."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Influencer":
            return await _response_403(request, db, "Acesso restrito a influencers.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("pages/influencer-area.html", context)


@app.get("/influencers-loja", response_class=HTMLResponse)
async def influencers_loja(request: Request, db: Session = Depends(get_db)):
    """Painel de influencers para CA (Loja)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role or user.role.nome != "Cliente Administrador":
            return await _response_403(request, db, "Acesso restrito a Cliente Administrador.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    context = await get_template_context_async(request, db)
    return await _render_template_async("pages/influencers-loja.html", context)


@app.get("/manual", response_class=HTMLResponse)
async def manual(request: Request, db: Session = Depends(get_db)):
    """
    Manual do sistema — voltado ao Cliente Administrador (CA).
    Auxilia no gerenciamento do negócio na plataforma; acessível a todos os usuários autenticados.
    """
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check

    context = await get_template_context_async(request, db)
    return await _render_template_async("pages/manual.html", context)


def filter_changelog_for_users(markdown_text: str) -> str:
    """Filtra o changelog removendo detalhes técnicos e mantendo apenas informações relevantes para usuários finais"""
    
    lines = markdown_text.split('\n')
    filtered_lines = []
    skip_until_header = False
    current_section_level = 0
    
    # Seções técnicas a remover completamente (por emoji ou texto)
    technical_section_markers = [
        '🗄️ Banco de Dados',
        '🏗️ Modelo SQLAlchemy',
        '📋 Schemas Pydantic',
        '🔌 API REST',
        '💻 JavaScript',
        '📋 Arquivos Modificados',
        '🔧 Melhorias Técnicas',
        '📝 Notas',
    ]
    
    # Palavras-chave técnicas que indicam linhas a remover
    technical_keywords = [
        'SCHEMA ATUALIZADO',
        'RESPOSTA API',
        'PROCESSAMENTO API',
        'ENDPOINT',
        'CRIAÇÃO:',
        'ATUALIZAÇÃO:',
        'CARREGAMENTO:',
        'EAGER LOADING',
        'REGISTRO:',
        'TRY-CATCH',
        'VERIFICAÇÕES:',
        'FORMATAÇÃO:',
        'LOGS DE DEBUG',
        'NOVA TABELA:',
        'RELACIONAMENTO:',
        'CONSTRAINT:',
        'SCRIPT SQL:',
        'NOVO MODELO:',
        'NOVO SCHEMA:',
        'NOVA API:',
        'ENDPOINTS DISPONÍVEIS:',
        'NOVAS FUNÇÕES:',
        'ATUALIZAÇÕES:',
        'IMPORTS:',
        'ESTRUTURA:',
        'LOCALIZAÇÃO:',
        'POSICIONAMENTO:',
        'INTEGRAÇÃO:',
        'COLSPAN:',
        'app/schemas/',
        'app/api/',
        'app/models/',
        'app/static/js/',
        'app/templates/',
        'app/database/',
        'joinedload',
        'Optional[',
        'ForeignKey',
        'BaseModel',
        'INT, PK',
        'VARCHAR',
        'TEXT',
        'DATETIME',
        'AUTO_INCREMENT',
        'nullable=True',
        'one-to-many',
        'relationship',
        'POST /api',
        'GET /api',
        'PUT /api',
        'DELETE /api',
    ]
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Detectar headers
        is_header = stripped.startswith('#')
        header_level = 0
        if is_header:
            header_level = len(stripped) - len(stripped.lstrip('#'))
        
        # Verificar se é uma seção técnica
        is_technical_section = any(marker in line for marker in technical_section_markers)
        
        # Se encontrar uma seção técnica, pular até o próximo header do mesmo nível ou superior
        if is_technical_section and is_header:
            skip_until_header = True
            current_section_level = header_level
            continue
        
        # Se estiver pulando, verificar se encontrou um novo header
        if skip_until_header:
            if is_header:
                # Se encontrou um header do mesmo nível ou superior, parar de pular
                if header_level <= current_section_level:
                    # Verificar se o novo header também é técnico
                    if not any(marker in line for marker in technical_section_markers):
                        skip_until_header = False
                    else:
                        current_section_level = header_level
                        continue
                else:
                    continue
            else:
                continue
        
        # Remover linhas que contêm palavras-chave técnicas
        if any(keyword in line for keyword in technical_keywords):
            continue
        
        # Manter linhas relevantes para usuários
        # Simplificar linguagem técnica
        simplified_line = line
        
        # Substituir termos técnicos por linguagem amigável
        replacements = {
            '**PROBLEMA CORRIGIDO:**': '**Correção:**',
            '**NOVA SEÇÃO:**': '**Novo:**',
            '**EXIBIÇÃO:**': '**Agora exibe:**',
            '**ORDENAÇÃO:**': '**Ordenado por:**',
            '**CONDIÇÃO:**': '**Observação:**',
            '**NOVO MODAL:**': '**Nova janela:**',
            '**MODAL ATUALIZADO:**': '**Janela atualizada:**',
            '**NOVO CAMPO:**': '**Novo campo:**',
            '**NOVA COLUNA:**': '**Nova coluna na tabela:**',
            '**BOTÃO:**': '**Novo botão:**',
            '**CAMPOS DO FORMULÁRIO:**': '**Campos disponíveis:**',
            '**ENSAIOS EXCENTRICIDADE:**': '**Ensaios de Excentricidade:**',
            '**RESULTADOS ENSAIOS:**': '**Resultados dos Ensaios:**',
            '**ENSAIOS MOBILIDADE:**': '**Ensaios de Mobilidade:**',
        }
        
        for old, new in replacements.items():
            simplified_line = simplified_line.replace(old, new)
        
        # Remover linhas vazias excessivas
        if not simplified_line.strip():
            if filtered_lines and not filtered_lines[-1].strip():
                continue
        
        filtered_lines.append(simplified_line)
    
    # Remover seções vazias e limpar
    result = '\n'.join(filtered_lines)
    
    # Remover múltiplas linhas vazias
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # Remover linhas que ficaram vazias após remoção de conteúdo
    result = re.sub(r'^####\s*$', '', result, flags=re.MULTILINE)
    result = re.sub(r'^###\s*$', '', result, flags=re.MULTILINE)
    
    return result

def markdown_to_html(markdown_text: str) -> str:
    """Converte markdown básico para HTML"""
    
    html = markdown_text
    
    # Preservar blocos de código antes de processar
    code_blocks = []
    code_block_pattern = r'```([\s\S]*?)```'
    
    def replace_code_block(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"
    
    html = re.sub(code_block_pattern, replace_code_block, html)
    
    # Headers (processar do mais específico para o mais genérico)
    html = re.sub(r'^#### (.*)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # Horizontal rules (antes de processar listas)
    html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)
    
    # Processar listas não ordenadas
    lines = html.split('\n')
    in_list = False
    result_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Verificar se é item de lista (pode começar com - ou *)
        if stripped.startswith('- ') or (stripped.startswith('* ') and not stripped.startswith('**')):
            if not in_list:
                result_lines.append('<ul>')
                in_list = True
            # Remover o marcador de lista
            content = stripped[2:].strip() if stripped.startswith('- ') else stripped[2:].strip()
            result_lines.append(f'<li>{content}</li>')
        else:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            result_lines.append(line)
    
    if in_list:
        result_lines.append('</ul>')
    
    html = '\n'.join(result_lines)
    
    # Bold (depois de processar listas para não interferir)
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    
    # Italic (cuidado para não conflitar com bold)
    html = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', html)
    
    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', html)
    
    # Inline code (após preservar blocos e processar outras formatações)
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # Restaurar blocos de código
    for i, code_block in enumerate(code_blocks):
        # Remover os marcadores de código (```)
        code_content = code_block.replace('```', '').strip()
        # Detectar linguagem se houver (primeira linha)
        lines = code_content.split('\n', 1)
        if len(lines) > 0 and lines[0] and not lines[0].startswith(' ') and len(lines[0].split()) == 1:
            lang = lines[0].strip()
            code_content = lines[1] if len(lines) > 1 else ''
            html = html.replace(f"__CODE_BLOCK_{i}__", f'<pre><code class="language-{lang}">{code_content}</code></pre>')
        else:
            html = html.replace(f"__CODE_BLOCK_{i}__", f'<pre><code>{code_content}</code></pre>')
    
    # Processar parágrafos (agrupar linhas consecutivas que não são headers, listas, etc)
    # Dividir por linhas duplas primeiro
    sections = re.split(r'\n\n+', html)
    processed_sections = []
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        # Se já é um elemento HTML (header, lista, pre, hr), não envolver em <p>
        if re.match(r'^<(h[1-6]|ul|ol|pre|hr|p)', section):
            processed_sections.append(section)
        else:
            # Envolver em parágrafo
            processed_sections.append(f'<p>{section}</p>')
    
    html = '\n\n'.join(processed_sections)
    
    # Limpar parágrafos vazios e duplicados
    html = re.sub(r'<p>\s*</p>', '', html)
    html = re.sub(r'<p>(<h[1-6]>)', r'\1', html)
    html = re.sub(r'(</h[1-6]>)</p>', r'\1', html)
    html = re.sub(r'<p>(<ul>)', r'\1', html)
    html = re.sub(r'(</ul>)</p>', r'\1', html)
    html = re.sub(r'<p>(<pre>)', r'\1', html)
    html = re.sub(r'(</pre>)</p>', r'\1', html)
    html = re.sub(r'<p>(<hr>)', r'\1', html)
    html = re.sub(r'(</hr>)</p>', r'\1', html)
    
    return html

@app.get("/changelog", response_class=HTMLResponse)
async def changelog(request: Request, db: Session = Depends(get_db)):
    """Página de Changelog"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    # Ler o arquivo CHANGELOG.md (main.py está na raiz do projeto)
    changelog_path = os.path.join(os.path.dirname(__file__), "CHANGELOG.md")
    changelog_content = ""
    
    try:
        if os.path.exists(changelog_path):
            with open(changelog_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()
                # Filtrar conteúdo técnico para usuários finais
                filtered_content = filter_changelog_for_users(markdown_content)
                # Converter markdown para HTML
                changelog_content = markdown_to_html(filtered_content)
        else:
            changelog_content = "<h1>Changelog</h1><p>Arquivo CHANGELOG.md não encontrado.</p>"
    except Exception as e:
        changelog_content = f"<h1>Erro ao carregar Changelog</h1><p>Erro: {str(e)}</p>"
    
    context = await get_template_context_async(request, db)
    context["changelog_content"] = changelog_content
    return await _render_template_async("pages/changelog.html", context)

# ============================================================================
# ROTAS DE NEGÓCIOS
# ============================================================================

@app.get("/negocio/dashboard", response_class=HTMLResponse)
async def negocio_dashboard(request: Request, db: Session = Depends(get_db)):
    """Dashboard de negócios (vendas, estoque e ordem de serviço)"""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check

    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)

        payload = AuthConfig.verify_token(token)
        perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar o dashboard de negócios")
        if perm_check:
            return perm_check
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user or not user.role:
            return RedirectResponse(url="/login", status_code=302)

        has_permission = (user.role.nome == "Superadministrador") or db.query(Permissao).join(
            RolePermissao, RolePermissao.permissao_id == Permissao.id
        ).filter(
            RolePermissao.role_id == user.role_id,
            Permissao.modulo.in_(["negocios.venda", "negocios.estoque", "negocios.ordem-servico"]),
            Permissao.acao == 'visualizar',
            Permissao.ativo == True
        ).first()

        if not has_permission:
            return await _response_403(request, db, "Você não tem permissão para acessar o dashboard de negócios")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)

    context = await get_template_context_async(request, db)
    return await _render_template_async("meu_negocio/dashboard.html", context)

@app.get("/negocio/venda", response_class=HTMLResponse)
async def negocio_venda(request: Request, db: Session = Depends(get_db)):
    """Página de vendas de negócios. Acesso: permissão módulo negocios ou pdv (get_user_permissions)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_any_module_permission(request, db, ["negocios", "pdv"], "Você não tem permissão para acessar o módulo de vendas")
    if perm_check:
        return perm_check
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("meu_negocio/vendas/index.html", context)

@app.get("/negocio/venda/pdv", response_class=HTMLResponse)
async def negocio_venda_pdv(request: Request, db: Session = Depends(get_db)):
    """Página PDV Mobile-First para frente de caixa. Acesso: permissão módulo negocios ou pdv (get_user_permissions)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_any_module_permission(request, db, ["negocios", "pdv"], "Você não tem permissão para acessar o PDV")
    if perm_check:
        return perm_check
    
    context = await get_template_context_async(request, db)
    context["pdv_static_version"] = PDV_STATIC_VERSION
    response = await _render_template_async("meu_negocio/vendas/pdv.html", context)
    # Evita cache da página no tablet para sempre carregar JS/CSS atualizados
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@app.get("/negocio/venda/pdv/manifest.webmanifest", include_in_schema=False)
async def negocio_venda_pdv_manifest():
    """Manifest PWA dedicado do PDV."""
    return FileResponse(
        "app/static/pwa/pdv-manifest.webmanifest",
        media_type="application/manifest+json",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/negocio/venda/pdv/sw.js", include_in_schema=False)
async def negocio_venda_pdv_service_worker():
    """Service Worker com escopo restrito ao PDV."""
    return FileResponse(
        "app/static/pwa/pdv-sw.js",
        media_type="application/javascript",
        headers={
            "Service-Worker-Allowed": "/negocio/venda/pdv",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )



@app.get("/negocio/caixa", response_class=HTMLResponse)
async def negocio_caixa(request: Request, db: Session = Depends(get_db)):
    """Página de caixa: aberturas, fechamentos, sangria e suprimento (Fase 3.2 – /api/v1/aberturas-caixa)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar o Caixa")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    return await _render_template_async("meu_negocio/caixa/index.html", context)


@app.get("/negocio/configuracoes-cupom", response_class=HTMLResponse)
async def negocio_configuracoes_cupom(request: Request, db: Session = Depends(get_db)):
    """Configuração de impressão de cupom (modo automático/manual e tipo não fiscal/fiscal). CA, Admin ou SuperAdmin."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para configurar o cupom")
    if perm_check:
        return perm_check
    user_role = (request.state.user.role.nome if getattr(request.state, "user", None) and getattr(request.state.user, "role", None) else "") or ""
    if user_role not in ("Superadministrador", "Administrador", "Cliente Administrador"):
        return await _render_template_async("errors/403.html", await get_template_context_async(request, db), status_code=403)
    context = await get_template_context_async(request, db)
    return await _render_template_async("meu_negocio/configuracoes_cupom.html", context)


@app.get("/negocio/recebiveis", response_class=HTMLResponse)
async def negocio_recebiveis(request: Request, db: Session = Depends(get_db)):
    """Página Recebíveis: configuração de recebimento (gateway) e pendências – o que o estabelecimento vendeu a receber."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar Recebíveis")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    return await _render_template_async("meu_negocio/pagamentos/index.html", context)


@app.get("/negocio/pagamentos", response_class=HTMLResponse)
async def negocio_pagamentos_redirect(request: Request):
    """Redirect legado: Pagamentos → Recebíveis (evita quebrar links antigos)."""
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/negocio/recebiveis", status_code=302)


@app.get("/negocio/recebiveis/comprovante/{transaction_uuid}", response_class=HTMLResponse)
async def negocio_recebiveis_comprovante(
    request: Request,
    transaction_uuid: str,
    db: Session = Depends(get_db),
):
    """Comprovante de pagamento (imprimível) para transação paga."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar Recebíveis")
    if perm_check:
        return perm_check
    from datetime import datetime, timezone

    from app.core.scope import get_cliente_scope

    tx = (
        db.query(PaymentTransaction)
        .options(joinedload(PaymentTransaction.pedido))
        .filter(PaymentTransaction.uuid == transaction_uuid)
        .first()
    )
    if not tx:
        return await _render_template_async(
            "errors/404.html",
            await get_template_context_async(request, db),
            status_code=404,
        )
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    from app.models.usuario import Usuario
    user = db.query(Usuario).options(joinedload(Usuario.role)).filter(Usuario.id == user_id).first()
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    role_nome = user.role.nome if getattr(user, "role", None) else None
    cliente_id_token = getattr(request.state, "cliente_id", None)
    scope = get_cliente_scope(db, user.id, role_nome, cliente_id_token)
    allowed = scope.allowed_ids if scope.must_filter_by_cliente() else None
    if allowed is not None and tx.cliente_id not in allowed:
        return await _render_template_async(
            "errors/403.html",
            await get_template_context_async(request, db),
            status_code=403,
        )
    status_lower = (tx.status or "").lower()
    status_labels = {"paid": "Pago", "authorized": "Autorizado", "pending": "Pendente", "failed": "Falhou"}
    status_label = status_labels.get(status_lower, status_lower)
    status_class = "paid" if status_lower in ("paid", "authorized") else "authorized"
    valor = f"{float(tx.amount or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    paid_at_str = ""
    if tx.paid_at and hasattr(tx.paid_at, "strftime"):
        paid_at_str = tx.paid_at.strftime("%d/%m/%Y %H:%M")
    method_labels = {"pix": "PIX", "credit": "Cartão de crédito", "debit": "Cartão de débito", "boleto": "Boleto"}
    payment_method_label = method_labels.get((tx.payment_method or "").lower(), tx.payment_method or "-")
    context = {
        "request": request,
        "uuid": tx.uuid,
        "numero_pedido": tx.pedido.numero_pedido if tx.pedido else None,
        "comprador_nome": tx.pedido.comprador_nome if tx.pedido else None,
        "valor": valor,
        "payment_method": payment_method_label,
        "status_label": status_label,
        "status_class": status_class,
        "paid_at": paid_at_str,
        "provider_transaction_id": tx.provider_transaction_id,
        "data_geracao": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M"),
    }
    return await _render_template_async("meu_negocio/pagamentos/comprovante.html", context)


@app.get("/negocio/estoque", response_class=HTMLResponse)
async def negocio_estoque(request: Request, db: Session = Depends(get_db)):
    """Página de estoque de negócios. Usa produtos do estabelecimento (produtos_cliente) = mesma base da Entrada NFe."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar o módulo de estoque")
    if perm_check:
        return perm_check
    try:
        context = await get_template_context_async(request, db)
        if not context.get("user_id"):
            return RedirectResponse(url="/login", status_code=302)
        perms = context.get("user_permissions") or []
        if "negocios.estoque" not in perms and "negocios" not in perms and context.get("user_role") != "Superadministrador":
            return await _response_403(request, db, "Você não tem permissão para acessar o módulo de estoque")
        from app.core.scope import get_empresa_fiscal_cliente_id
        from app.models import Cliente
        from app.models.produto_cliente import ProdutoCliente
        is_superadmin = context.get("user_role") == "Superadministrador"
        context["is_superadmin_estoque"] = is_superadmin
        context["estoque_lojas"] = []
        context["estoque_modo_global"] = False
        query_cliente_id = request.query_params.get("cliente_id")
        if is_superadmin and query_cliente_id == "todos":
            context["estoque_cliente_id"] = ""
            context["estoque_cliente_nome"] = "Todas as lojas"
            context["estoque_modo_global"] = True
        elif is_superadmin and query_cliente_id and query_cliente_id.isdigit():
            cid = int(query_cliente_id)
            cli = db.query(Cliente).filter(Cliente.id == cid).first()
            if cli:
                context["estoque_cliente_id"] = cid
                context["estoque_cliente_nome"] = (cli.nome or "").strip()
            else:
                context["estoque_cliente_id"] = None
                context["estoque_cliente_nome"] = None
        else:
            cid = get_empresa_fiscal_cliente_id(
                db,
                context.get("user_id"),
                context.get("user_role"),
                getattr(request.state, "cliente_id", None),
            )
            if cid is not None:
                cid = int(cid)
                cli = db.query(Cliente).filter(Cliente.id == cid).first()
                context["estoque_cliente_id"] = cid
                context["estoque_cliente_nome"] = (cli.nome or "").strip() if cli else ("Estabelecimento #%s" % cid)
            else:
                context["estoque_cliente_id"] = None
                context["estoque_cliente_nome"] = None
        if is_superadmin:
            from sqlalchemy import distinct
            lojas_com_produto = (
                db.query(Cliente.id, Cliente.nome)
                .filter(Cliente.id.in_(
                    db.query(distinct(ProdutoCliente.cliente_id))
                ))
                .order_by(Cliente.nome)
                .all()
            )
            context["estoque_lojas"] = [{"id": c.id, "nome": (c.nome or "").strip()} for c in lojas_com_produto]
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    return await _render_template_async("meu_negocio/estoque/index.html", context)


@app.get("/negocio/estoque/categorias", response_class=HTMLResponse)
async def negocio_estoque_categorias(request: Request, db: Session = Depends(get_db)):
    """Página de cadastro de categorias de material (estoque). Apenas Superadministrador."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    try:
        context = await get_template_context_async(request, db)
        if not context.get("user_id"):
            return RedirectResponse(url="/login", status_code=302)
        if context.get("user_role") != "Superadministrador":
            return await _response_403(request, db, "Cadastro de categorias de material é restrito ao Superadministrador.")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    return await _render_template_async("meu_negocio/estoque/categorias.html", context)


@app.get("/negocio/estoque/pendencias", response_class=HTMLResponse)
async def negocio_estoque_pendencias(request: Request, db: Session = Depends(get_db)):
    """Página de correção de pendências (imagem, tipo, categoria, preço de venda, descrição). Mesma permissão que estoque."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar o módulo de estoque")
    if perm_check:
        return perm_check
    try:
        context = await get_template_context_async(request, db)
        if not context.get("user_id"):
            return RedirectResponse(url="/login", status_code=302)
        perms = context.get("user_permissions") or []
        if "negocios.estoque" not in perms and "negocios" not in perms and context.get("user_role") != "Superadministrador":
            return await _response_403(request, db, "Você não tem permissão para acessar o módulo de estoque")
        from app.core.scope import get_empresa_fiscal_cliente_id
        from app.models import Cliente
        cid = get_empresa_fiscal_cliente_id(
            db,
            context.get("user_id"),
            context.get("user_role"),
            getattr(request.state, "cliente_id", None),
        )
        if cid is not None:
            cid = int(cid)
            cli = db.query(Cliente).filter(Cliente.id == cid).first()
            context["estoque_cliente_id"] = cid
            context["estoque_cliente_nome"] = (cli.nome or "").strip() if cli else ("Estabelecimento #%s" % cid)
        else:
            context["estoque_cliente_id"] = None
            context["estoque_cliente_nome"] = None
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    return await _render_template_async("meu_negocio/estoque/pendencias.html", context)


@app.get("/negocio/estoque/tipos-material", response_class=HTMLResponse)
async def negocio_estoque_tipos_material(request: Request, db: Session = Depends(get_db)):
    """Página de cadastro de tipos de material (estoque). Mesma permissão que estoque."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar o módulo de estoque")
    if perm_check:
        return perm_check
    try:
        context = await get_template_context_async(request, db)
        if not context.get("user_id"):
            return RedirectResponse(url="/login", status_code=302)
        perms = context.get("user_permissions") or []
        if "negocios.estoque" not in perms and "negocios" not in perms and context.get("user_role") != "Superadministrador":
            return await _response_403(request, db, "Você não tem permissão para acessar o módulo de estoque")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    return await _render_template_async("meu_negocio/estoque/tipos_material.html", context)


@app.get("/negocio/fornecedores", response_class=HTMLResponse)
async def negocio_fornecedores(
    request: Request,
    cliente_id: Optional[int] = Query(None, description="Estabelecimento (Superadmin ou usuário com vários clientes no escopo)"),
    db: Session = Depends(get_db),
):
    """Página de cadastro de fornecedores por estabelecimento. Permissão: negocios.estoque ou Superadministrador."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar o módulo de negócios")
    if perm_check:
        return perm_check
    try:
        context = await get_template_context_async(request, db)
        if not context.get("user_id"):
            return RedirectResponse(url="/login", status_code=302)
        perms = context.get("user_permissions") or []
        if "negocios.estoque" not in perms and "negocios" not in perms and context.get("user_role") != "Superadministrador":
            return await _response_403(request, db, "Você não tem permissão para acessar fornecedores")
        from app.core.scope import get_allowed_cliente_ids, get_empresa_fiscal_cliente_id
        from app.models import Cliente
        from app.models.fornecedor_cliente import FornecedorCliente
        from app.models.produto_cliente import ProdutoCliente
        from sqlalchemy import distinct

        uid = int(context["user_id"])
        role_nome = context.get("user_role")
        token_cid = getattr(request.state, "cliente_id", None)
        allowed = get_allowed_cliente_ids(db, uid, role_nome, token_cid)
        is_superadmin = role_nome == "Superadministrador"
        context["fornecedores_is_superadmin"] = is_superadmin
        context["fornecedores_lojas"] = []
        context["fornecedores_mostrar_seletor"] = False

        cid_resolvido: Optional[int] = None
        try:
            if is_superadmin:
                if cliente_id is not None:
                    cli_q = db.query(Cliente).filter(Cliente.id == int(cliente_id)).first()
                    if cli_q:
                        cid_resolvido = int(cliente_id)
                if cid_resolvido is None:
                    ef = get_empresa_fiscal_cliente_id(db, uid, role_nome, token_cid)
                    cid_resolvido = int(ef) if ef is not None else None
                ids_prod = [r[0] for r in db.query(distinct(ProdutoCliente.cliente_id)).all()]
                ids_for = [r[0] for r in db.query(distinct(FornecedorCliente.cliente_id)).all()]
                union_ids = sorted(set(ids_prod) | set(ids_for))
                if cid_resolvido is not None and int(cid_resolvido) not in union_ids:
                    union_ids = sorted(set(union_ids) | {int(cid_resolvido)})
                if union_ids:
                    lojas_rows = db.query(Cliente).filter(Cliente.id.in_(union_ids)).order_by(Cliente.nome).all()
                    context["fornecedores_lojas"] = [{"id": c.id, "nome": (c.nome or "").strip()} for c in lojas_rows]
                context["fornecedores_mostrar_seletor"] = True
            elif (role_nome or "").strip() == "Cliente Administrador":
                # CA = um estabelecimento operacional (empresa fiscal); mesmo critério da Entrada NF-e — sem seletor.
                context["fornecedores_mostrar_seletor"] = False
                ef = get_empresa_fiscal_cliente_id(db, uid, role_nome, token_cid)
                if ef is not None:
                    cid_resolvido = int(ef)
                elif allowed and len(allowed) == 1:
                    cid_resolvido = int(allowed[0])
                else:
                    cid_resolvido = None
            else:
                if allowed and len(allowed) > 1:
                    context["fornecedores_mostrar_seletor"] = True
                    lojas_rows = db.query(Cliente).filter(Cliente.id.in_(allowed)).order_by(Cliente.nome).all()
                    context["fornecedores_lojas"] = [{"id": c.id, "nome": (c.nome or "").strip()} for c in lojas_rows]
                    if cliente_id is not None and int(cliente_id) in allowed:
                        cid_resolvido = int(cliente_id)
                    else:
                        ef = get_empresa_fiscal_cliente_id(db, uid, role_nome, token_cid)
                        if ef is not None and int(ef) in allowed:
                            cid_resolvido = int(ef)
                        else:
                            cid_resolvido = int(allowed[0])
                elif allowed and len(allowed) == 1:
                    cid_resolvido = int(allowed[0])
                else:
                    ef = get_empresa_fiscal_cliente_id(db, uid, role_nome, token_cid)
                    cid_resolvido = int(ef) if ef is not None else None

            if cid_resolvido is not None:
                cli = db.query(Cliente).filter(Cliente.id == cid_resolvido).first()
                context["fornecedores_cliente_id"] = cid_resolvido
                context["fornecedores_cliente_nome"] = (cli.nome or "").strip() if cli else ("Estabelecimento #%s" % cid_resolvido)
            else:
                context["fornecedores_cliente_id"] = None
                context["fornecedores_cliente_nome"] = None
        except Exception as e_scope:
            log_error("Fornecedores: erro ao resolver estabelecimento", exc_info=e_scope, user_id=str(uid))
            context["fornecedores_cliente_id"] = None
            context["fornecedores_cliente_nome"] = None
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    return await _render_template_async("meu_negocio/fornecedores/index.html", context)


@app.get("/negocio/entrada-nfe", response_class=HTMLResponse)
async def negocio_entrada_nfe(request: Request, db: Session = Depends(get_db)):
    """Página de entrada de notas NFe (importação XML e conciliação). Estabelecimento fixo = CA logado."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar o módulo de estoque")
    if perm_check:
        return perm_check
    try:
        context = await get_template_context_async(request, db)
        if not context.get("user_id"):
            return RedirectResponse(url="/login", status_code=302)
        perms = context.get("user_permissions") or []
        if "negocios.estoque" not in perms and "negocios" not in perms and context.get("user_role") != "Superadministrador":
            return await _response_403(request, db, "Você não tem permissão para acessar a entrada de notas NFe")
        # Estabelecimento fixo = empresa fiscal real do usuário (CA = seu estabelecimento; respeita tenant)
        try:
            from app.core.scope import get_empresa_fiscal_cliente_id
            from app.models import Cliente
            cid = get_empresa_fiscal_cliente_id(
                db,
                context.get("user_id"),
                context.get("user_role"),
                getattr(request.state, "cliente_id", None),
            )
            if cid is not None:
                cid = int(cid)
                cli = db.query(Cliente).filter(Cliente.id == cid).first()
                context["entrada_nfe_cliente_id"] = cid
                context["entrada_nfe_cliente_nome"] = (cli.nome or "").strip() if cli else ("Estabelecimento #%s" % cid)
            else:
                context["entrada_nfe_cliente_id"] = None
                context["entrada_nfe_cliente_nome"] = None
        except Exception as e_scope:
            log_error("Entrada NFe: erro ao resolver empresa fiscal", exc_info=e_scope, user_id=str(context.get("user_id")) if context.get("user_id") is not None else None)
            context["entrada_nfe_cliente_id"] = None
            context["entrada_nfe_cliente_nome"] = None
    except Exception as e:
        log_error("Entrada NFe: erro na rota /negocio/entrada-nfe", exc_info=e)
        return RedirectResponse(url="/login", status_code=302)
    return await _render_template_async("meu_negocio/entrada_nfe/index.html", context)


@app.get("/negocio/entrada-nfe/{nfe_id:int}/conciliar", response_class=HTMLResponse)
async def negocio_entrada_nfe_conciliar(
    request: Request,
    nfe_id: int,
    cliente_id: int = Query(..., description="ID do estabelecimento"),
    db: Session = Depends(get_db),
):
    """Página de conciliação de itens da NF-e importada."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar o módulo de estoque")
    if perm_check:
        return perm_check
    try:
        context = await get_template_context_async(request, db)
        if not context.get("user_id"):
            return RedirectResponse(url="/login", status_code=302)
        perms = context.get("user_permissions") or []
        if "negocios.estoque" not in perms and "negocios" not in perms and context.get("user_role") != "Superadministrador":
            return await _response_403(request, db, "Você não tem permissão para acessar a conciliação")
        context["nfe_id"] = nfe_id
        context["cliente_id"] = cliente_id
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    return await _render_template_async("meu_negocio/entrada_nfe/conciliar.html", context)


@app.get("/negocio/financeiro", response_class=HTMLResponse)
async def negocio_financeiro(request: Request, db: Session = Depends(get_db)):
    """Página de financeiro de negócios (resumo financeiro). Um contexto, permissão via user_permissions."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar o módulo financeiro")
    if perm_check:
        return perm_check
    try:
        context = await get_template_context_async(request, db)
        if not context.get("user_id"):
            return RedirectResponse(url="/login", status_code=302)
        perms = context.get("user_permissions") or []
        if "negocios.financeiro" not in perms and "negocios" not in perms and context.get("user_role") != "Superadministrador":
            return await _response_403(request, db, "Você não tem permissão para acessar o módulo financeiro")
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    return await _render_template_async("meu_negocio/financeiro/index.html", context)


@app.get("/negocio/relatorios", response_class=HTMLResponse)
async def negocio_relatorios(request: Request, db: Session = Depends(get_db)):
    """Página de relatórios operacionais de negócios (Fase 4.2): fechamento caixa, vendas período, mais vendidos, custo x venda, cancelamentos."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar relatórios de negócios")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    if not context.get("user_id"):
        return RedirectResponse(url="/login", status_code=302)
    return await _render_template_async("meu_negocio/relatorios.html", context)


@app.get("/negocio/ordem-servico", response_class=HTMLResponse)
async def negocio_ordem_servico(request: Request, db: Session = Depends(get_db)):
    """Página de ordem de serviço de negócios"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    # Verificar permissões específicas para ordem_servico
    try:
        token = request.cookies.get("pdv_solumatica_token")
        if not token:
            return RedirectResponse(url="/login", status_code=302)
        payload = AuthConfig.verify_token(token)
        perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar ordem de serviço")
        if perm_check:
            return perm_check
        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        
        if not user or not user.role:
            return RedirectResponse(url="/login", status_code=302)
        
        has_permission = (user.role.nome == "Superadministrador") or db.query(Permissao).join(
            RolePermissao, RolePermissao.permissao_id == Permissao.id
        ).filter(
            RolePermissao.role_id == user.role_id,
            Permissao.modulo == 'negocios.ordem-servico',
            Permissao.acao == 'visualizar',
            Permissao.ativo == True
        ).first()
        
        if not has_permission:
            return await _response_403(request, db, "Você não tem permissão para acessar o módulo de ordem de serviço")
            
    except Exception:
        return RedirectResponse(url="/login", status_code=302)
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("meu_negocio/ordem_de_servico/index.html", context)


@app.get("/negocio/orcamentos", response_class=HTMLResponse)
async def negocio_orcamentos(request: Request, db: Session = Depends(get_db)):
    """Página de orçamentos (módulo Orçamento e Pedido). Exige permissão negocios.orcamento:visualizar."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar orçamentos")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    perms = context.get("user_permissions") or []
    if "negocios.orcamento:visualizar" not in perms and context.get("user_role") != "Superadministrador":
        return await _response_403(request, db, "Você não tem permissão para acessar orçamentos")
    return await _render_template_async("meu_negocio/orcamentos/index.html", context)


@app.get("/negocio/orcamentos/novo", response_class=HTMLResponse)
async def negocio_orcamentos_novo(request: Request, db: Session = Depends(get_db)):
    """Formulário de novo orçamento."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar orçamentos")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    perms = context.get("user_permissions") or []
    if "negocios.orcamento:visualizar" not in perms and "negocios.orcamento:criar" not in perms and context.get("user_role") != "Superadministrador":
        return await _response_403(request, db, "Você não tem permissão para criar orçamento")
    context["orcamento_id"] = None
    return await _render_template_async("meu_negocio/orcamentos/form.html", context)


@app.get("/negocio/orcamentos/{orcamento_id:int}/editar", response_class=HTMLResponse)
async def negocio_orcamentos_editar(request: Request, orcamento_id: int, db: Session = Depends(get_db)):
    """Formulário de edição de orçamento (apenas rascunho)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar orçamentos")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    perms = context.get("user_permissions") or []
    if "negocios.orcamento:visualizar" not in perms and context.get("user_role") != "Superadministrador":
        return await _response_403(request, db, "Você não tem permissão para editar orçamento")
    context["orcamento_id"] = orcamento_id
    return await _render_template_async("meu_negocio/orcamentos/form.html", context)


@app.get("/negocio/pedidos", response_class=HTMLResponse)
async def negocio_pedidos(request: Request, db: Session = Depends(get_db)):
    """Página de pedidos (módulo Orçamento e Pedido). Exige permissão negocios.pedido:visualizar."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar pedidos")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    perms = context.get("user_permissions") or []
    if "negocios.pedido:visualizar" not in perms and context.get("user_role") != "Superadministrador":
        return await _response_403(request, db, "Você não tem permissão para acessar pedidos")
    context["minha_loja_cliente_id"] = getattr(request.state, "cliente_id", None)
    return await _render_template_async("meu_negocio/pedidos/index.html", context)


@app.get("/negocio/pedidos/novo", response_class=HTMLResponse)
async def negocio_pedidos_novo(request: Request, db: Session = Depends(get_db)):
    """Formulário de novo pedido."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar pedidos")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    perms = context.get("user_permissions") or []
    if "negocios.pedido:visualizar" not in perms and "negocios.pedido:criar" not in perms and context.get("user_role") != "Superadministrador":
        return await _response_403(request, db, "Você não tem permissão para criar pedido")
    context["pedido_id"] = None
    return await _render_template_async("meu_negocio/pedidos/form.html", context)


@app.get("/negocio/pedidos/{pedido_id:int}/editar", response_class=HTMLResponse)
async def negocio_pedidos_editar(request: Request, pedido_id: int, db: Session = Depends(get_db)):
    """Formulário de edição de pedido (apenas rascunho)."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar pedidos")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    perms = context.get("user_permissions") or []
    if "negocios.pedido:visualizar" not in perms and context.get("user_role") != "Superadministrador":
        return await _response_403(request, db, "Você não tem permissão para editar pedido")
    context["pedido_id"] = pedido_id
    return await _render_template_async("meu_negocio/pedidos/form.html", context)


@app.get("/negocio/pedidos/{pedido_id:int}/faturar", response_class=HTMLResponse)
async def negocio_pedidos_faturar(request: Request, pedido_id: int, db: Session = Depends(get_db)):
    """Tela de faturamento parcial do pedido."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar pedidos")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    perms = context.get("user_permissions") or []
    if "negocios.pedido:faturar" not in perms and context.get("user_role") != "Superadministrador":
        return await _response_403(request, db, "Você não tem permissão para faturar pedido")
    context["pedido_id"] = pedido_id
    return await _render_template_async("meu_negocio/pedidos/faturar.html", context)


@app.get("/negocio/marketplace", response_class=HTMLResponse)
async def negocio_marketplace(request: Request, db: Session = Depends(get_db)):
    """Página de gestão do marketplace (loja, anúncios). Exige marketplace:visualizar."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "marketplace:visualizar", "Você não tem permissão para acessar o Marketplace")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    return await _render_template_async("marketplace/index.html", context)


@app.get("/negocio/marketplace/minha-loja", response_class=HTMLResponse)
async def negocio_marketplace_minha_loja(request: Request, db: Session = Depends(get_db)):
    """Página da minha loja (configuração e anúncios). Exige marketplace:visualizar."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "marketplace:visualizar", "Você não tem permissão para acessar o Marketplace")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    context["minha_loja_cliente_id"] = getattr(request.state, "cliente_id", None)
    return await _render_template_async("marketplace/minha_loja.html", context)


@app.get("/negocio/marketplace/consumidores", response_class=HTMLResponse)
async def negocio_marketplace_consumidores(request: Request, db: Session = Depends(get_db)):
    """Listagem de consumidores do marketplace. Exige marketplace:visualizar."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "marketplace:visualizar", "Você não tem permissão para acessar o Marketplace")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    context["minha_loja_cliente_id"] = getattr(request.state, "cliente_id", None)
    return await _render_template_async("marketplace/consumidores.html", context)


@app.get("/negocio/marketplace/integracao/eventos", response_class=HTMLResponse)
async def negocio_marketplace_integracao_eventos(request: Request, db: Session = Depends(get_db)):
    """Listagem de eventos de integração CRM. Exige marketplace:visualizar."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "marketplace:visualizar", "Você não tem permissão para acessar o Marketplace")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    context["minha_loja_cliente_id"] = getattr(request.state, "cliente_id", None)
    return await _render_template_async("marketplace/integracao_eventos.html", context)


@app.get("/negocio/marketplace/logistica/entrega/{entrega_id:int}", response_class=HTMLResponse)
async def negocio_marketplace_logistica_entrega(request: Request, entrega_id: int, db: Session = Depends(get_db)):
    """Página de acompanhamento da entrega (timeline). Exige marketplace:visualizar."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "marketplace:visualizar", "Você não tem permissão para acessar o Marketplace")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    context["entrega_id"] = entrega_id
    return await _render_template_async("logistica/acompanhar_entrega.html", context)


@app.get("/negocio/marketplace/areas-entrega", response_class=HTMLResponse)
async def negocio_marketplace_areas_entrega(request: Request, db: Session = Depends(get_db)):
    """Página de áreas de entrega. SuperAdmin: gerencia todas as lojas. CA: visualiza áreas da própria loja."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "marketplace:visualizar", "Você não tem permissão para acessar o Marketplace")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    user = getattr(request.state, "user", None)
    if user and user.role:
        from app.core.scope import get_empresa_fiscal_cliente_id
        cid = get_empresa_fiscal_cliente_id(
            db, user.id, user.role.nome, getattr(request.state, "cliente_id", None)
        )
        context["minha_loja_cliente_id"] = cid
    else:
        context["minha_loja_cliente_id"] = None
    return await _render_template_async("marketplace/areas_entrega.html", context)


# ============================================================================
# VITRINE (loja pública - consumidor final)
# ============================================================================

async def _loja_context(request: Request, db: Session | None = None, **extra):
    """Contexto base para páginas da vitrine (consumidor_logado, consumidor_id, consumidor_nome quando logado, pdv_user_logado, request)."""
    logado = await _loja_consumidor_logado(request)
    base_url = _landing_base_url(request)
    ctx = {"request": request, "consumidor_logado": logado, "base_url": base_url or ""}
    if logado:
        ctx["consumidor_id"] = _loja_consumidor_id(request)
        if db is not None:
            ctx["consumidor_nome"] = _loja_consumidor_nome(request, db)
    ctx.setdefault("busca_q", "")
    ctx.setdefault("busca_ativa", False)
    # Verificar se usuário PDV está logado (para mostrar link "Painel" no header da vitrine)
    pdv_logado = False
    token_pdv = request.cookies.get("pdv_solumatica_token")
    if token_pdv:
        try:
            p = AuthConfig.verify_token(token_pdv)
            if p.get("sub"):
                pdv_logado = True
        except Exception:
            pass
    ctx["pdv_user_logado"] = pdv_logado
    ctx["csp_nonce"] = getattr(request.state, "csp_nonce", "")
    from app.services.marketing_vitrine_service import (
        marketing_vitrine_template_fallback,
        vitrine_index_template_context,
    )

    if db is not None:
        try:
            ctx["marketing_vitrine"] = vitrine_index_template_context(db)
        except Exception:
            ctx["marketing_vitrine"] = marketing_vitrine_template_fallback()
        try:
            nap_keys = [
                "marketplace_nome", "marketplace_endereco", "marketplace_cidade",
                "marketplace_uf", "marketplace_cep", "marketplace_telefone",
            ]
            rows = db.query(Configuracao).filter(Configuracao.chave.in_(nap_keys)).all()
            nap = {r.chave: r.valor for r in rows}
            ctx["nap"] = {
                "nome": nap.get("marketplace_nome", ""),
                "endereco": nap.get("marketplace_endereco", ""),
                "cidade": nap.get("marketplace_cidade", ""),
                "uf": nap.get("marketplace_uf", ""),
                "cep": nap.get("marketplace_cep", ""),
                "telefone": nap.get("marketplace_telefone", ""),
            }
        except Exception:
            ctx["nap"] = {}
    else:
        ctx["marketing_vitrine"] = marketing_vitrine_template_fallback()
    ctx.update(extra)
    if "seo" not in ctx:
        ctx["seo"] = None
    fb = (getattr(settings, "SEO_FB_APP_ID", None) or "").strip()
    ctx["seo_fb_app_id"] = fb if fb else None
    return ctx


def _normalize_public_loja_slug(raw_slug: str) -> str:
    slug = normalize_slug_or_404(raw_slug)
    if not SLUG_REGEX.match(slug):
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    return slug


def _slug_to_label(slug_value: str) -> str:
    return (slug_value or "").replace("-", " ").strip().title()


def _public_loja_display_name(loja: LojaMarketplace) -> str:
    nome = first_non_empty(
        [getattr(loja, "nome_fantasia", None), getattr(loja, "nome_loja", None)]
    )
    if nome:
        return nome.strip()
    return f"Loja {loja.id}"


def _absolute_url(base_url: str, path_or_url: str | None) -> str | None:
    if not path_or_url or not str(path_or_url).strip():
        return None
    raw = str(path_or_url).strip()
    if raw.startswith(("http://", "https://")):
        return raw
    if not base_url:
        return raw
    return f"{base_url.rstrip('/')}/" + raw.lstrip("/")


def _absolute_public_https_url(base_url: str, path_or_url: str | None) -> str | None:
    """URL absoluta para og:image / JSON-LD; None se não houver base pública ou path vazio."""
    if not path_or_url or not str(path_or_url).strip():
        return None
    raw = str(path_or_url).strip()
    if raw.startswith(("http://", "https://")):
        return raw
    bu = (base_url or "").strip()
    if not bu:
        return None
    base = bu.rstrip("/") + "/"
    joined = urljoin(base, raw.lstrip("/"))
    return (joined or "").strip() or None


def _og_image_url_with_cache_bust(image_url: str, updated_at: datetime.datetime | None) -> str:
    """Query lastmod para invalidar cache Meta quando o path do ficheiro não muda."""
    if not image_url or not updated_at:
        return image_url
    try:
        ts = int(updated_at.timestamp())
    except Exception:
        return image_url
    sep = "&" if "?" in image_url else "?"
    return f"{image_url}{sep}lastmod={ts}"


def _build_store_seo(loja: LojaMarketplace, base_url: str) -> dict:
    cidade_slug = (getattr(loja, "cidade_seo", None) or "").strip()
    categoria_slug = (getattr(loja, "categoria_principal", None) or "").strip()
    nome = _public_loja_display_name(loja)
    cidade_label = _slug_to_label(cidade_slug) if cidade_slug else ""
    categoria_label = _slug_to_label(categoria_slug) if categoria_slug else ""
    seo_on = bool(getattr(loja, "seo_enabled", True))
    if cidade_label and categoria_label:
        default_title = f"{nome} em {cidade_label} | {categoria_label}"
        default_description = f"Conheça {nome} em {cidade_label}. Encontre opções de {categoria_label.lower()} na vitrine Ibix."
        h1 = f"{nome} em {cidade_label}"
        texto_base_default = f"A {nome} atua em {cidade_label} no segmento de {categoria_label.lower()}, oferecendo produtos e atendimento pela vitrine Ibix."
    else:
        default_title = f"{nome} | Ibix"
        default_description = f"Conheça a loja {nome} na vitrine Ibix."
        h1 = nome
        texto_base_default = f"A loja {nome} oferece produtos e atendimento pela vitrine Ibix."
    manual_title = (getattr(loja, "seo_title", None) or "").strip() if seo_on else ""
    manual_desc = (getattr(loja, "seo_description", None) or "").strip() if seo_on else ""
    title = (manual_title or default_title)[:60]
    description = (manual_desc or default_description)[:160]
    canonical = f"{base_url}/{loja.slug}" if base_url else f"/{loja.slug}"
    texto_base = first_non_empty(
        [
            getattr(loja, "descricao_longa", None),
            getattr(loja, "descricao_curta", None),
            getattr(loja, "descricao", None),
        ]
    )
    if not (texto_base or "").strip():
        texto_base = texto_base_default
    og_raw = getattr(loja, "og_image_url", None)
    og_image = _absolute_url(base_url or "", og_raw) if og_raw else None
    return {
        "title": title,
        "description": description,
        "h1": h1,
        "canonical": canonical,
        "og_image": og_image,
        "texto_base": texto_base,
    }


def _build_loja_store_jsonld(loja: LojaMarketplace, base_url: str) -> dict | None:
    """JSON-LD Store (Schema.org) com endereço do estabelecimento — SEO local por loja."""
    c = getattr(loja, "cliente", None)
    if c is None:
        return None
    end = (getattr(c, "endereco", None) or "").strip()
    cidade = (getattr(c, "cidade", None) or "").strip()
    uf = (getattr(c, "uf", None) or "").strip()
    if not end or not cidade or not uf:
        return None
    slug = (getattr(loja, "slug", None) or "").strip()
    if not slug:
        return None
    nome = _public_loja_display_name(loja)
    store_url = f"{base_url.rstrip('/')}/{slug}" if base_url else f"/{slug}"
    addr: dict = {
        "@type": "PostalAddress",
        "streetAddress": end,
        "addressLocality": cidade,
        "addressRegion": uf.upper(),
        "addressCountry": "BR",
    }
    cep = (getattr(c, "cep", None) or "").strip()
    if cep:
        addr["postalCode"] = cep
    payload: dict = {
        "@context": "https://schema.org",
        "@type": "Store",
        "name": nome,
        "url": store_url,
        "address": addr,
    }
    tel = (getattr(c, "telefone", None) or "").strip()
    if tel:
        payload["telephone"] = tel
    logo_raw = getattr(loja, "logo_url", None)
    og_raw = getattr(loja, "og_image_url", None)
    img = _absolute_url(base_url or "", logo_raw) or _absolute_url(base_url or "", og_raw)
    if img:
        payload["image"] = img
    cid_seo = (getattr(loja, "cidade_seo", None) or "").strip()
    if cid_seo:
        loc_name = _slug_to_label(cid_seo)
        est_seo = (getattr(loja, "estado_seo", None) or "").strip()
        if est_seo:
            loc_name = f"{loc_name}, {est_seo.upper()}"
        payload["areaServed"] = {"@type": "City", "name": loc_name}
    return payload


def _build_category_seo(categoria_slug: str, cidade_slug: str, base_url: str) -> dict:
    categoria_label = _slug_to_label(categoria_slug)
    cidade_label = _slug_to_label(cidade_slug)
    title = f"{categoria_label} em {cidade_label} | Ibix"[:60]
    description = (
        f"Encontre {categoria_label.lower()} em {cidade_label}. Veja lojas, ofertas e contatos na Ibix."
    )[:160]
    canonical_path = f"/categoria/{categoria_slug}-{cidade_slug}"
    return {
        "title": title,
        "description": description,
        "h1": f"{categoria_label} em {cidade_label}",
        "canonical": f"{base_url}{canonical_path}" if base_url else canonical_path,
        "categoria_label": categoria_label,
        "cidade_label": cidade_label,
        "canonical_path": canonical_path,
    }


@app.get("/loja", response_class=HTMLResponse)
async def loja_landing(request: Request):
    """Landing institucional (Ibix)."""
    await check_loja_public_page_rate_limit(request)
    base_url = _landing_base_url(request)
    landing_ctx = {
        "request": request,
        "base_url": base_url,
        "canonical_path": "/loja",
        "contact_telefone": None,
        "contact_whatsapp": None,
        "contact_whatsapp_link": None,
    }
    return await _render_template_async("pages/landing.html", landing_ctx)


@app.get("/loja/categoria/{slug:path}", response_class=HTMLResponse)
async def loja_categoria(request: Request, slug: str, db: Session = Depends(get_db)):
    """Vitrine por categoria."""
    cat = db.query(CategoriaPlataforma).filter(
        CategoriaPlataforma.slug == slug, CategoriaPlataforma.ativa == True
    ).first()
    ctx = await _loja_context(
        request,
        db=db,
        categoria_slug=slug,
        categoria_id=cat.id if cat else None,
        categoria_nome=cat.nome if cat else None,
    )
    return await _render_template_async("loja/index.html", ctx)


@app.get("/loja/produto/{anuncio_id:int}", response_class=HTMLResponse)
async def loja_produto_redirect(request: Request, anuncio_id: int, db: Session = Depends(get_db)):
    """Redirect 301 da URL numerica antiga para a URL amigavel com slug."""
    anuncio = None
    try:
        anuncio = db.query(AnuncioPlataforma).filter(
            AnuncioPlataforma.id == anuncio_id,
            AnuncioPlataforma.status == "publicado",
        ).first()
    except Exception:
        pass
    if not anuncio:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return RedirectResponse(url=produto_slug_url(anuncio.titulo, anuncio.id), status_code=301)


@app.get("/loja/produto/{slug_id:path}", response_class=HTMLResponse)
async def loja_produto(request: Request, slug_id: str, db: Session = Depends(get_db)):
    """Detalhe do produto na vitrine (URL amigavel). SSR parcial para SEO (titulo, descricao, imagem, JSON-LD Product)."""
    anuncio_id = parse_produto_slug_id(slug_id)
    if anuncio_id is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if getattr(settings, "VITRINE_UTM_ATTRIBUTION_ENABLED", True):
        from app.core.loja_attribution import (
            set_vitrine_share_attribution_cookie,
            strip_utm_params_from_path_query,
        )

        src = (request.query_params.get("utm_source") or "").strip().lower()
        if src == "compartilhamento":
            clean_path = strip_utm_params_from_path_query(request)
            raw_q = request.url.query
            current = request.url.path + (("?" + raw_q) if raw_q else "")
            if clean_path != current:
                resp = RedirectResponse(url=clean_path, status_code=302)
                set_vitrine_share_attribution_cookie(resp, request)
                return resp
    anuncio_ssr = None
    try:
        anuncio_ssr = (
            db.query(AnuncioPlataforma)
            .options(
                joinedload(AnuncioPlataforma.produto_cliente),
                joinedload(AnuncioPlataforma.categoria),
                joinedload(AnuncioPlataforma.loja),
            )
            .filter(
                AnuncioPlataforma.id == anuncio_id,
                AnuncioPlataforma.status == "publicado",
            )
            .first()
        )
    except Exception:
        pass
    canonical_path = None
    if anuncio_ssr:
        canonical_path = produto_slug_url(anuncio_ssr.titulo, anuncio_ssr.id)
        if f"/loja/produto/{slug_id}" != canonical_path:
            return RedirectResponse(url=canonical_path, status_code=301)
    ssr = {}
    if anuncio_ssr:
        from app.api.v1.loja import _imagens_anuncio_ou_fallback

        base_pub = (_landing_base_url(request) or "").strip()
        imgs = _imagens_anuncio_ou_fallback(anuncio_ssr, db)
        og_override = (getattr(anuncio_ssr, "og_image_url", None) or "").strip()
        first_rel = og_override or (imgs[0] if imgs else "")
        if not base_pub and first_rel:
            logger.warning(
                "SEO_PUBLIC_BASE_URL vazio em /loja/produto anuncio_id=%s: og:image absoluta e "
                "canonical https indisponiveis; preview social pode usar o logo padrao.",
                anuncio_ssr.id,
            )
        img_abs = _absolute_public_https_url(base_pub, first_rel)
        if img_abs:
            img_abs = _og_image_url_with_cache_bust(img_abs, getattr(anuncio_ssr, "updated_at", None))
        legacy_abs = (_absolute_url(base_pub, first_rel) or first_rel or "").strip()
        display_imagem = img_abs or legacy_abs or first_rel
        pc = anuncio_ssr.produto_cliente
        cat = anuncio_ssr.categoria
        loja = anuncio_ssr.loja
        ssr = {
            "ssr_titulo": anuncio_ssr.titulo or "",
            "ssr_descricao": (anuncio_ssr.descricao or "")[:200],
            "ssr_imagem": display_imagem,
            "ssr_imagens": imgs,
            "ssr_preco": float(anuncio_ssr.preco_promocional or anuncio_ssr.preco_original or 0),
            "ssr_preco_original": float(anuncio_ssr.preco_original or 0),
            "ssr_disponivel": True,
            "ssr_canonical_path": canonical_path,
            "ssr_sku": (pc.codigo if pc else None) or "",
            "ssr_brand": (pc.fabricante if pc else None) or "",
            "ssr_category_name": (cat.nome if cat else None) or "",
            "ssr_category_slug": (cat.slug if cat else None) or "",
            "ssr_seller_name": (getattr(loja, "nome_loja", None) or "") if loja else "",
            "ssr_price_valid_until": f"{datetime.date.today().year}-12-31",
        }
        seo: dict = {}
        if base_pub:
            seo["canonical"] = f"{base_pub.rstrip('/')}{canonical_path}"
        if img_abs:
            seo["og_image"] = img_abs
            titulo_og = (anuncio_ssr.titulo or "Produto").strip()
            if titulo_og:
                seo["og_image_alt"] = titulo_og[:200]
        if any(seo):
            ssr["seo"] = seo
        else:
            ssr["seo"] = None
    return await _render_template_async(
        "loja/produto.html", await _loja_context(request, db=db, anuncio_id=anuncio_id, **ssr)
    )


@app.get("/loja/busca", response_class=HTMLResponse)
async def loja_busca(request: Request, db: Session = Depends(get_db)):
    """Busca na vitrine. Pesquisa produtos (via API) e também lojas (Tenant CA) por
    nome / fantasia / slug / razão social / cidade. Lojas casadas aparecem em uma
    faixa no topo dos resultados; cada card abre /{slug} (vitrine filtrada por loja).
    """
    q = request.query_params.get("q", "").strip()
    lojas_busca: list[dict] = []
    if q:
        from sqlalchemy import func, or_

        termo = f"%{q}%"
        rows = (
            db.query(LojaMarketplace, Cliente)
            .join(Cliente, Cliente.id == LojaMarketplace.cliente_id)
            .filter(
                LojaMarketplace.status == "ativo",
                LojaMarketplace.slug.isnot(None),
                or_(
                    LojaMarketplace.nome_loja.ilike(termo),
                    LojaMarketplace.nome_fantasia.ilike(termo),
                    LojaMarketplace.slug.ilike(termo),
                    Cliente.nome.ilike(termo),
                    Cliente.cidade.ilike(termo),
                ),
            )
            .order_by(
                func.coalesce(
                    LojaMarketplace.nome_fantasia, LojaMarketplace.nome_loja
                ).asc()
            )
            .limit(12)
            .all()
        )
        for loja, cli in rows:
            nome_publico = _public_loja_display_name(loja)
            lojas_busca.append(
                {
                    "id": loja.id,
                    "slug": loja.slug,
                    "nome": nome_publico,
                    "logo_url": (loja.logo_url or "").strip() or None,
                    "descricao_curta": (loja.descricao_curta or "").strip() or None,
                    "categoria_principal": loja.categoria_principal or None,
                    "cidade": (cli.cidade or "").strip() or None,
                    "uf": (cli.uf or "").strip().upper() or None,
                    "endereco": (cli.endereco or "").strip() or None,
                    "url": f"/{loja.slug}",
                }
            )
    ctx = await _loja_context(
        request,
        db=db,
        busca_q=q,
        busca_ativa=len(q) > 0,
        lojas_busca=lojas_busca,
    )
    return await _render_template_async("loja/index.html", ctx)


@app.get("/loja/cadastro", response_class=HTMLResponse)
async def loja_cadastro(request: Request, db: Session = Depends(get_db)):
    """Cadastro de consumidor."""
    return await _render_template_async("loja/cadastro.html", await _loja_context(request, db=db))


@app.get("/loja/login", response_class=HTMLResponse)
async def loja_login(request: Request, db: Session = Depends(get_db)):
    """Login consumidor."""
    return await _render_template_async("loja/login.html", await _loja_context(request, db=db))


@app.get("/loja/esqueci-senha", response_class=HTMLResponse)
async def loja_esqueci_senha(request: Request, db: Session = Depends(get_db)):
    """Página Esqueci minha senha (Loja)."""
    context = await _loja_context(request, db=db)
    return await _render_template_async("loja/esqueci_senha.html", context)


@app.get("/loja/redefinir-senha", response_class=HTMLResponse)
async def loja_redefinir_senha(request: Request, token: Optional[str] = None, db: Session = Depends(get_db)):
    """Página Redefinir senha (Loja) com token na URL."""
    context = await _loja_context(request, db=db)
    context["token"] = token or ""
    return await _render_template_async("loja/redefinir_senha.html", context)


@app.get("/loja/logout", response_class=HTMLResponse)
async def loja_logout_page(request: Request):
    """Logout consumidor: remove cookie e redireciona para a vitrine."""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key=COOKIE_LOJA_CONSUMIDOR)
    return response


@app.get("/loja/termos-de-uso", response_class=HTMLResponse)
async def loja_termos_de_uso(request: Request, db: Session = Depends(get_db)):
    """Termos de uso para o comprador da loja (marketplace). Página pública, não exige login."""
    return await _render_template_async(
        "loja/termos-de-uso.html", await _loja_context(request, db=db)
    )


@app.get("/loja/minha-conta", response_class=HTMLResponse)
async def loja_minha_conta(request: Request, db: Session = Depends(get_db)):
    """Minha conta (consumidor)."""
    return await _render_template_async(
        "loja/minha_conta.html", await _loja_context(request, db=db)
    )


@app.get("/loja/meus-pedidos", response_class=HTMLResponse)
async def loja_meus_pedidos(request: Request, db: Session = Depends(get_db)):
    """Meus pedidos (consumidor)."""
    return await _render_template_async(
        "loja/meus_pedidos.html", await _loja_context(request, db=db)
    )


@app.get("/loja/carrinho", response_class=HTMLResponse)
async def loja_carrinho(request: Request, db: Session = Depends(get_db)):
    """Carrinho."""
    return await _render_template_async(
        "loja/carrinho.html", await _loja_context(request, db=db)
    )


@app.get("/loja/checkout", response_class=HTMLResponse)
async def loja_checkout(request: Request, db: Session = Depends(get_db)):
    """Checkout."""
    return await _render_template_async(
        "loja/checkout.html", await _loja_context(request, db=db)
    )


@app.get("/loja/obrigado", response_class=HTMLResponse)
async def loja_obrigado(request: Request, db: Session = Depends(get_db)):
    """Página pós-compra."""
    return await _render_template_async(
        "loja/obrigado.html", await _loja_context(request, db=db)
    )


@app.get("/loja/pagamento/sucesso", response_class=HTMLResponse)
async def loja_pagamento_sucesso(request: Request, db: Session = Depends(get_db)):
    """Retorno do gateway: só exibe sucesso quando pagamento CONFIRMADO (status_pagamento=pago).
    Reconcilia com MP se pedido pendente; se após reconciliação ainda não estiver pago, redireciona.
    Diretriz: nunca exibir confirmação de venda sem pagamento real (validade jurídica)."""
    from app.core.billing_config import get_mp_access_token
    from app.models import (
        MarketplaceCheckoutSession,
        MarketplaceCheckoutSessionPedido,
        PaymentTransaction,
        PedidoMarketplace,
    )
    from app.services.payments.providers_marketplace import get_marketplace_provider
    from app.services.payments.webhook_marketplace_service import process_payment_notification
    from fastapi.responses import RedirectResponse

    session_uuid = (request.query_params.get("session") or "").strip()
    pedido_id_raw = request.query_params.get("pedido")

    if session_uuid:
        sess = db.query(MarketplaceCheckoutSession).filter(MarketplaceCheckoutSession.uuid == session_uuid).first()
        if not sess:
            return RedirectResponse(url="/loja", status_code=302)
        tx = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.checkout_session_id == sess.id,
                PaymentTransaction.is_active == True,
            )
            .order_by(PaymentTransaction.id.desc())
            .first()
        )
        if not tx:
            return RedirectResponse(url="/loja", status_code=302)
        links = (
            db.query(MarketplaceCheckoutSessionPedido)
            .filter(MarketplaceCheckoutSessionPedido.session_id == sess.id)
            .order_by(MarketplaceCheckoutSessionPedido.sort_order.asc())
            .all()
        )
        pids = [link.pedido_id for link in links]
        pedidos = db.query(PedidoMarketplace).filter(PedidoMarketplace.id.in_(pids)).all()
        if not pedidos:
            return RedirectResponse(url="/loja", status_code=302)
        any_pending = any((p.status_pagamento or "").lower() != "pago" for p in pedidos)
        if any_pending:
            token = get_mp_access_token(db)
            if token:
                provider = get_marketplace_provider("mercadopago")
                ext_ref = f"mcs:{session_uuid}"
                mp_payment = None
                if tx.provider_transaction_id:
                    mp_payment = provider.fetch_payment(tx.provider_transaction_id, {"access_token": token})
                if not mp_payment:
                    mp_payment = provider.search_payment_by_reference(ext_ref, {"access_token": token})
                if mp_payment:
                    mp_status = (mp_payment.get("status") or "").lower()
                    if mp_status in ("approved", "authorized"):
                        process_payment_notification(db, tx, mp_status, mp_payment)
                        db.commit()
                        for p in pedidos:
                            db.refresh(p)
        all_paid = all((p.status_pagamento or "").lower() == "pago" for p in pedidos)
        if not all_paid:
            aid = pedidos[0].id
            return RedirectResponse(
                url=f"/loja/pagamento/cancelado?pedido={aid}&session={session_uuid}",
                status_code=302,
            )
        ctx = await _loja_context(request, db=db)
        ctx["pedido"] = pedidos[0]
        ctx["pedidos_sessao"] = pedidos
        ctx["numero_pedido"] = ", ".join(p.numero_pedido for p in pedidos)
        return await _render_template_async("loja/pagamento_sucesso.html", ctx)

    if not pedido_id_raw:
        return RedirectResponse(url="/loja", status_code=302)

    try:
        pedido_id = int(pedido_id_raw)
    except (ValueError, TypeError):
        return RedirectResponse(url="/loja", status_code=302)

    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not pedido:
        return RedirectResponse(url="/loja", status_code=302)

    if (pedido.status_pagamento or "").lower() == "pendente":
        token = get_mp_access_token(db)
        if token:
            provider = get_marketplace_provider("mercadopago")
            tx = (
                db.query(PaymentTransaction)
                .filter(
                    PaymentTransaction.pedido_id == pedido_id,
                    PaymentTransaction.is_active == True,
                )
                .order_by(PaymentTransaction.id.desc())
                .first()
            )
            if tx:
                mp_payment = None
                if tx.provider_transaction_id:
                    mp_payment = provider.fetch_payment(tx.provider_transaction_id, {"access_token": token})
                if not mp_payment:
                    mp_payment = provider.search_payment_by_reference(str(pedido_id), {"access_token": token})
                if mp_payment:
                    mp_status = (mp_payment.get("status") or "").lower()
                    if mp_status in ("approved", "authorized"):
                        process_payment_notification(db, tx, mp_status, mp_payment)
                        db.commit()
                        db.refresh(pedido)

    if (pedido.status_pagamento or "").lower() != "pago":
        return RedirectResponse(
            url=f"/loja/pagamento/cancelado?pedido={pedido_id}", status_code=302
        )

    ctx = await _loja_context(request, db=db)
    ctx["pedido"] = pedido
    ctx["numero_pedido"] = pedido.numero_pedido
    return await _render_template_async("loja/pagamento_sucesso.html", ctx)


@app.get("/loja/pagamento/cancelado", response_class=HTMLResponse)
async def loja_pagamento_cancelado(request: Request, db: Session = Depends(get_db)):
    """Retorno do gateway: pagamento cancelado ou falhou."""
    return await _render_template_async(
        "loja/pagamento_cancelado.html", await _loja_context(request, db=db)
    )


@app.get("/loja/completar-cadastro", response_class=HTMLResponse)
async def loja_completar_cadastro(request: Request, db: Session = Depends(get_db)):
    """Página para GUEST definir senha e ativar conta (link pós-compra)."""
    return await _render_template_async(
        "loja/completar_cadastro.html", await _loja_context(request, db=db)
    )


@app.get("/loja/acompanhar-pedido", response_class=HTMLResponse)
async def loja_acompanhar_pedido(request: Request, db: Session = Depends(get_db)):
    """Página para acompanhar pedido. Se consumidor logado + numero_pedido na URL, renderiza o pedido no servidor."""
    ctx = await _loja_context(request, db=db)
    numero = (request.query_params.get("numero_pedido") or "").strip()
    if numero and ctx.get("consumidor_logado") and db is not None:
        consumidor_id = None
        token = request.cookies.get(COOKIE_LOJA_CONSUMIDOR) or (
            (request.headers.get("Authorization") or "").replace("Bearer ", "").strip()
        )
        if token:
            try:
                payload = AuthConfig.verify_token(token)
                if payload.get("tipo") == "consumidor":
                    consumidor_id = int(payload.get("sub", 0) or 0)
            except Exception:
                pass
        if consumidor_id:
            pedido = db.query(PedidoMarketplace).filter(
                PedidoMarketplace.numero_pedido == numero,
                PedidoMarketplace.comprador_id == consumidor_id,
            ).first()
            if pedido:
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
                ctx["pedido_acompanhar"] = {
                    "id": pedido.id,
                    "numero_pedido": pedido.numero_pedido,
                    "status_pedido": pedido.status_pedido or "",
                    "status_pagamento": pedido.status_pagamento or "",
                    "status_entrega": getattr(pedido, "status_entrega", "") or "pendente",
                    "total": float(pedido.total or 0),
                    "created_at": pedido.created_at.isoformat() if getattr(pedido.created_at, "isoformat", None) else None,
                    "itens": itens_resumo,
                    "timeline": timeline,
                }
    return await _render_template_async("loja/acompanhar_pedido.html", ctx)


# --- Área Entregador (logística local) ---
@app.get("/entregador/login", response_class=HTMLResponse)
async def entregador_login_page(request: Request):
    """Login do entregador."""
    return await _render_template_async("entregador/login.html", {"request": request})


@app.get("/entregador/logout", response_class=HTMLResponse)
async def entregador_logout_page(request: Request):
    """Logout entregador: remove cookie e redireciona para login."""
    response = RedirectResponse(url="/entregador/login", status_code=302)
    response.delete_cookie(key="entregador_token")
    return response


@app.get("/entregador/disponiveis", response_class=HTMLResponse)
async def entregador_disponiveis(request: Request):
    """Entregas disponíveis para aceitar."""
    return await _render_template_async("entregador/disponiveis.html", {"request": request})


@app.get("/entregador/minhas-entregas", response_class=HTMLResponse)
async def entregador_minhas_entregas(request: Request):
    """Minhas entregas (entregador)."""
    return await _render_template_async("entregador/minhas_entregas.html", {"request": request})


@app.get("/entregador/entrega/{entrega_id:int}", response_class=HTMLResponse)
async def entregador_detalhe_entrega(request: Request, entrega_id: int):
    """Detalhe da entrega e ações de status."""
    return await _render_template_async("entregador/detalhe.html", {"request": request, "entrega_id": entrega_id})


@app.get("/negocio/relatorio-conversao-orcamentos", response_class=HTMLResponse)
async def negocio_relatorio_conversao_orcamentos(request: Request, db: Session = Depends(get_db)):
    """Página de relatório de conversão orçamentos → pedidos."""
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    perm_check = await check_html_module_permission(request, db, "negocios", "Você não tem permissão para acessar relatórios de negócios")
    if perm_check:
        return perm_check
    context = await get_template_context_async(request, db)
    perms = context.get("user_permissions") or []
    if "negocios.orcamento:visualizar" not in perms and context.get("user_role") != "Superadministrador":
        return await _response_403(request, db, "Você não tem permissão para acessar este relatório")
    return await _render_template_async("meu_negocio/relatorio_conversao_orcamentos.html", context)


# Rotas de UI
@app.get("/ui/forms", response_class=HTMLResponse)
async def ui_forms(request: Request, db: Session = Depends(get_db)):
    """Página de formulários"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("ui/forms.html", context)

@app.get("/ui/buttons", response_class=HTMLResponse)
async def ui_buttons(request: Request, db: Session = Depends(get_db)):
    """Página de botões"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("ui/buttons.html", context)

@app.get("/ui/cards", response_class=HTMLResponse)
async def ui_cards(request: Request, db: Session = Depends(get_db)):
    """Página de cards"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("ui/cards.html", context)

@app.get("/ui/typography", response_class=HTMLResponse)
async def ui_typography(request: Request, db: Session = Depends(get_db)):
    """Página de tipografia"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("ui/typography.html", context)

@app.get("/ui/icons", response_class=HTMLResponse)
async def ui_icons(request: Request, db: Session = Depends(get_db)):
    """Página de ícones"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("ui/icons.html", context)

@app.get("/ui/charts", response_class=HTMLResponse)
async def ui_charts(request: Request, db: Session = Depends(get_db)):
    """Página de gráficos"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("ui/charts.html", context)

@app.get("/ui/maps", response_class=HTMLResponse)
async def ui_maps(request: Request, db: Session = Depends(get_db)):
    """Página de mapas"""
    # Verificar autenticação
    auth_check = await check_auth_for_html(request, db)
    if auth_check:
        return auth_check
    
    context = await get_template_context_async(request, db)
    return await _render_template_async("ui/maps.html", context)


@app.get("/categoria", response_class=RedirectResponse)
async def categoria_local_sem_slug_redirect():
    """URL local exige /categoria/{categoria}-{cidade}; sem isso, /categoria colidia com /{slug}='categoria'."""
    return RedirectResponse(url="/", status_code=301)


@app.get("/lojas-parceiras", response_class=HTMLResponse)
async def lojas_parceiras_page(request: Request, db: Session = Depends(get_db)):
    """Página pública 'Lojas Parceiras': lista todas as lojas ativas (logo + endereço).
    Cada card aponta para /{slug} (vitrine filtrada por loja). Listagem é carregada
    via /api/v1/loja/lojas-parceiras (paginação + filtros).
    """
    await check_loja_public_page_rate_limit(request)
    return await _render_template_async(
        "loja/lojas_parceiras.html",
        await _loja_context(request, db=db),
    )


@app.get("/{slug}", response_class=HTMLResponse)
async def loja_publica_por_slug(slug: str, request: Request, db: Session = Depends(get_db)):
    """Vitrine pública por slug da loja no domínio raiz."""
    await check_loja_public_page_rate_limit(request)
    slug_norm = _normalize_public_loja_slug(slug)
    from sqlalchemy import func
    loja = (
        db.query(LojaMarketplace)
        .options(joinedload(LojaMarketplace.cliente))
        .filter(
            func.lower(LojaMarketplace.slug) == slug_norm,
            LojaMarketplace.status == "ativo",
        )
        .first()
    )
    if not loja:
        hist = db.query(LojaSlugHistory).join(
            LojaMarketplace, LojaMarketplace.id == LojaSlugHistory.loja_id
        ).filter(
            func.lower(LojaSlugHistory.slug_antigo) == slug_norm,
            LojaMarketplace.status == "ativo",
            LojaMarketplace.slug.isnot(None),
        ).first()
        if hist and hist.loja and hist.loja.slug:
            return RedirectResponse(url=f"/{hist.loja.slug}", status_code=301)
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    base_pub = _landing_base_url(request)
    seo = _build_store_seo(loja, base_pub)
    q = request.query_params.get("q", "").strip()
    cat_s = (getattr(loja, "categoria_principal", None) or "").strip()
    cid_s = (getattr(loja, "cidade_seo", None) or "").strip()
    loja_store_jsonld = _build_loja_store_jsonld(loja, base_pub or "")
    ctx = await _loja_context(
        request,
        db=db,
        loja_slug_context=slug_norm,
        loja_nome_context=_public_loja_display_name(loja),
        loja_categoria_context=cat_s or None,
        loja_cidade_context=cid_s or None,
        loja_categoria_label=_slug_to_label(cat_s) if cat_s else None,
        loja_cidade_label=_slug_to_label(cid_s) if cid_s else None,
        descricao_publica=seo["texto_base"],
        seo=seo,
        loja_store_jsonld=loja_store_jsonld,
        busca_q=q,
        busca_ativa=len(q) > 0,
        vitrine_hero_titulo_uma_linha=bool(
            getattr(loja, "vitrine_hero_titulo_uma_linha", False)
        ),
    )
    return await _render_template_async("loja/index.html", ctx)


@app.get("/categoria/{categoria_cidade_slug:path}", response_class=HTMLResponse)
async def categoria_local_publica(categoria_cidade_slug: str, request: Request, db: Session = Depends(get_db)):
    """Página SEO de categoria+cidade com listagem de lojas."""
    await check_loja_public_page_rate_limit(request)
    slug_norm = normalize_slug_or_404(categoria_cidade_slug)
    lojas = (
        db.query(LojaMarketplace)
        .filter(
            LojaMarketplace.status == "ativo",
            LojaMarketplace.slug_categoria_cidade == slug_norm,
            LojaMarketplace.slug.isnot(None),
        )
        .order_by(LojaMarketplace.nome_loja.asc())
        .all()
    )
    if not lojas:
        raise HTTPException(status_code=404, detail="Categoria local não encontrada")
    primeira = lojas[0]
    categoria_slug = (primeira.categoria_principal or "").strip()
    cidade_slug = (primeira.cidade_seo or "").strip()
    if not categoria_slug or not cidade_slug:
        raise HTTPException(status_code=404, detail="Categoria local não encontrada")
    seo = _build_category_seo(categoria_slug, cidade_slug, _landing_base_url(request))
    ctx = await _loja_context(
        request,
        db=db,
        seo=seo,
        categoria_slug=categoria_slug,
        cidade_slug=cidade_slug,
        lojas_categoria=lojas,
        descricao_publica=f"Encontre empresas de {seo['categoria_label']} em {seo['cidade_label']} na Ibix.",
        busca_ativa=False,
    )
    return await _render_template_async("loja/categoria_local.html", ctx)


@app.get("/api/health")
async def health_check():
    """Verificação de saúde da API"""
    from app.core.redis_client import redis_available
    return {
        "status": "healthy",
        "service": "PDV Ibix",
        "version": "1.0.0",
        "redis": "connected" if redis_available() else "disconnected",
    }

@app.get("/api/database/status")
async def database_status(request: Request):
    """Verificação de status do banco. Em produção, restrito por DATABASE_STATUS_ALLOWED_IPS (IPs separados por vírgula)."""
    if (os.getenv("ENV", "").lower() == "production"):
        allowed_ips = os.getenv("DATABASE_STATUS_ALLOWED_IPS", "").strip()
        ips = [i.strip() for i in allowed_ips.split(",") if i.strip()]
        if not ips:
            raise HTTPException(status_code=404, detail="Not Found")
        client_ip = get_client_ip(request)
        if client_ip not in ips:
            raise HTTPException(status_code=404, detail="Not Found")
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
            return {"status": "connected", "database": "pdv_solumatica", "message": "Database connection successful"}
    except Exception as e:
        log_error("database_status erro: %s", e, exc_info=True)
        return {"status": "error", "database": "pdv_solumatica", "message": "Database connection failed"}

# ─── Deep Links (Mobile App) ─────────────────────────────────
@app.get("/.well-known/assetlinks.json")
async def android_asset_links():
    pkg = settings.ANDROID_PACKAGE_NAME
    sha = settings.ANDROID_SHA256_FINGERPRINT
    if not pkg or not sha:
        return JSONResponse(content=[], status_code=200)
    return JSONResponse(content=[{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": pkg,
            "sha256_cert_fingerprints": [sha],
        },
    }])


_SECURITY_TXT = (
    "Contact: mailto:seguranca@ibix.com.br\n"
    "Preferred-Languages: pt-BR, en\n"
    "Canonical: https://www.ibix.com.br/.well-known/security.txt\n"
    "Expires: 2027-04-13T00:00:00.000Z\n"
)


@app.get("/.well-known/security.txt", response_class=PlainTextResponse, include_in_schema=False)
async def security_txt():
    return _SECURITY_TXT


@app.get("/.well-known/apple-app-site-association")
async def apple_app_site_association():
    bundle = settings.IOS_BUNDLE_ID
    team = settings.IOS_TEAM_ID
    if not bundle or not team:
        return JSONResponse(content={"applinks": {"apps": [], "details": []}}, status_code=200)
    return JSONResponse(content={
        "applinks": {
            "apps": [],
            "details": [{
                "appID": f"{team}.{bundle}",
                "paths": ["/loja/*", "/vitrine/*", "/produto/*"],
            }],
        },
    })


# Configuração para iniciar o servidor
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 