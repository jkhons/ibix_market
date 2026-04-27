# PDV Ibix - Google Custom Search (imagens) para cadastro de produto
"""Proxy ao Google Custom Search JSON API (searchType=image) e download seguro de URL para base64."""
import base64
import ipaddress
import socket
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from ...core.google_cse_config import (
    build_search_query,
    get_google_cse_api_key,
    get_google_cse_engine_id,
    google_cse_credentials_configured,
)
from ...core.middleware import forbid_cliente_access, get_current_user
from ...core.scope import resolve_tenant_pagador
from ...database.connection import get_db
from ...models import Usuario
from ...services.google_cse_quota import log_search_success, release_search_quota, reserve_search_quota

router = APIRouter(prefix="/integracoes", tags=["Integrações"])

GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
MAX_FETCH_BYTES = 5 * 1024 * 1024

BYPASS_QUOTA_ROLES = frozenset({"Superadministrador", "Administrador"})


def _detail_google_cse_http_error(status_code: int, msg: str) -> str:
    if status_code == 403 and "Custom Search JSON API" in (msg or ""):
        return (
            "Google recusou acesso à Custom Search JSON API. No projeto Google Cloud onde a chave foi criada: "
            "vincule faturamento ao projeto (comum ser obrigatório); ative a API "
            "'Custom Search API' em Biblioteca; em Credenciais, a chave deve incluir essa API nas restrições. "
            f"Detalhe Google: {msg}"
        )
    return f"Google Custom Search: {msg}"


def _role_nome(user: Usuario) -> str:
    return (user.role.nome if user.role else "") or ""


def _host_is_safe(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    if p.scheme not in ("http", "https"):
        return False
    host = p.hostname
    if not host:
        return False
    hl = host.lower()
    if hl == "localhost" or hl.startswith("127."):
        return False
    try:
        for res in socket.getaddrinfo(host, None):
            ip_str = res[4][0]
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
    except Exception:
        return False
    return True


@router.get("/google-custom-search-imagens/cota", response_model=dict)
def cota_google_imagens(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Limite e uso do dia para o tenant do usuário (buscas Google imagem)."""
    role = _role_nome(current_user)
    if role in BYPASS_QUOTA_ROLES:
        return {"aplica_cota": False, "limite_diario": None, "uso_hoje": None, "restante": None}
    tenant_id = resolve_tenant_pagador(db, current_user.id, role)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant não identificado para cota de busca de imagens.",
        )
    from app.models import Tenant

    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    lim = int(t.google_cse_limite_diario or 0)
    uso = int(t.google_cse_uso_dia or 0)
    restante = max(0, lim - uso) if lim > 0 else 0
    return {
        "aplica_cota": True,
        "limite_diario": lim,
        "uso_hoje": uso,
        "restante": restante if lim > 0 else 0,
    }


@router.get("/google-custom-search-imagens", response_model=dict)
async def buscar_imagens_google(
    q: str = Query(..., min_length=1, max_length=500, description="Nome base do produto (sufixo NCM/ficha técnica vem da config)"),
    num: int = Query(10, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Busca imagens via Google Custom Search API (searchType=image). Cota por tenant no GET."""
    if not google_cse_credentials_configured(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Custom Search não configurado. Configure API Key e Search Engine ID no painel Superadmin ou variáveis de ambiente.",
        )
    api_key = get_google_cse_api_key(db)
    cx = get_google_cse_engine_id(db)
    q_final = build_search_query(q, db)
    if not q_final.strip():
        raise HTTPException(status_code=400, detail="Termo de busca vazio após montagem")

    role = _role_nome(current_user)
    tenant_id: Optional[int] = None
    use_quota = role not in BYPASS_QUOTA_ROLES

    if use_quota:
        tenant_id = resolve_tenant_pagador(db, current_user.id, role)
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Busca de imagens disponível apenas para contas vinculadas a um estabelecimento (tenant).",
            )
        reserve_search_quota(db, tenant_id)

    params = {
        "key": api_key,
        "cx": cx,
        "q": q_final,
        "searchType": "image",
        "num": num,
        "safe": "active",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(GOOGLE_CSE_URL, params=params)
    except httpx.RequestError as e:
        if use_quota and tenant_id:
            release_search_quota(db, tenant_id)
            db.commit()
        raise HTTPException(status_code=502, detail=f"Falha ao contatar Google: {e}") from e

    if r.status_code != 200:
        if use_quota and tenant_id:
            release_search_quota(db, tenant_id)
            db.commit()
        try:
            err = r.json()
            msg = err.get("error", {}).get("message", r.text[:200])
        except Exception:
            msg = r.text[:200]
        raise HTTPException(
            status_code=502,
            detail=_detail_google_cse_http_error(r.status_code, msg),
        )

    data = r.json()
    items_out: List[dict] = []
    for it in data.get("items") or []:
        if not isinstance(it, dict):
            continue
        link = it.get("link") or ""
        img_meta = it.get("image") if isinstance(it.get("image"), dict) else {}
        thumb = it.get("thumbnailLink") or img_meta.get("thumbnailLink") or ""
        items_out.append(
            {
                "title": it.get("title") or "",
                "link": link,
                "thumbnail": thumb,
                "displayLink": it.get("displayLink") or "",
            }
        )

    if use_quota and tenant_id:
        log_search_success(db, tenant_id, current_user.id)
        db.commit()
    else:
        db.rollback()

    return {
        "items": items_out,
        "searchInformation": data.get("searchInformation"),
        "query_efetiva": q_final,
    }


class FetchImagemBody(BaseModel):
    url: HttpUrl = Field(..., description="URL da imagem (ex.: link retornado pela busca)")


@router.post("/google-custom-search-imagens/fetch", response_model=dict)
async def fetch_imagem_url(
    body: FetchImagemBody,
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Baixa a imagem no servidor (evita CORS no navegador) e devolve data URL base64 para o cadastro."""
    url_str = str(body.url)
    if not _host_is_safe(url_str):
        raise HTTPException(status_code=400, detail="URL inválida ou não permitida para download")
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(
                url_str,
                headers={"User-Agent": "PDV-Ibix/1.0 (produto-imagem)"},
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Falha ao baixar imagem: {e}") from e

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Download retornou HTTP {resp.status_code}")

    ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    if not ctype.startswith("image/"):
        raise HTTPException(status_code=400, detail="URL não retornou uma imagem (content-type inválido)")

    raw = resp.content
    if len(raw) > MAX_FETCH_BYTES:
        raise HTTPException(status_code=400, detail="Imagem excede 5 MB")

    b64 = base64.b64encode(raw).decode("ascii")
    mime = ctype if ctype else "image/jpeg"
    data_url = f"data:{mime};base64,{b64}"
    return {"data_url": data_url, "content_type": mime, "size": len(raw)}
