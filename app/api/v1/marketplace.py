# PDV Ibix - API Marketplace (gestão loja, anúncios, categorias, sync)
"""APIs de gestão do marketplace: categorias plataforma, loja do CA, anúncios, sincronização. Escopo por ClienteScope."""
import base64
import json
import os
import re
import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, require_permission, require_superadmin
from ...core.scope import ClienteScope
from ...core.slug_utils import (
    ensure_slug_not_reserved,
    generate_unique_slug,
    normalize_category_slug,
    normalize_city_slug,
    normalize_slug_or_400,
    slugify,
)
from ...database.connection import get_db
from ...models import (
    AnuncioPlataforma,
    CategoriaPlataforma,
    Cliente,
    ConsumidorMarketplace,
    ExtratoLoja,
    IntegrationEvent,
    LojaAreaEntrega,
    LojaMarketplace,
    LojaSlugHistory,
    PedidoItemMarketplace,
    PedidoMarketplace,
    ProdutoCliente,
    StatusPedidoMarketplace,
    SyncControle,
    Tenant,
    Usuario,
)
from ...schemas.cupom import CupomConteudoResponse
from ...schemas.marketplace import (
    VITRINE_HERO_NOME_FANTASIA_MAX,
    AnuncioPlataformaCreate,
    AnuncioPlataformaResponse,
    AnuncioPlataformaUpdate,
    CategoriaPlataformaCreate,
    CategoriaPlataformaResponse,
    CategoriaPlataformaUpdate,
    ExtratoLojaResponse,
    LojaAreaEntregaCreate,
    LojaAreaEntregaResponse,
    LojaAreaEntregaUpdate,
    LojaMarketplaceCreate,
    LojaMarketplaceResponse,
    LojaMarketplaceUpdate,
    PedidoItemGestaoResponse,
    PedidoMarketplaceResponse,
    PedidoMarketplaceUpdate,
    ReparacaoCompradorRequest,
    ReparacaoCompradorResultado,
    StatusPedidoMarketplaceCreate,
    StatusPedidoMarketplaceResponse,
    StatusPedidoMarketplaceUpdate,
)
from ...schemas.marketplace_taxa import MarketplaceTaxasVigentesResponse
from ...services.cupom_receipt import gerar_cupom_resumo_pedido_marketplace
from ...services.marketplace_reparacao_comprador_service import reparar_comprador_pedidos
from ...services.marketplace_taxa_service import montar_preview, resolver_regra_e_payload
from ...services.pedido_status_evento_service import registrar_pedido_status_evento
from ...services.websocket_manager import publish_event as publish_consumidor_event
from ...services.reserva_estoque_marketplace_service import restore_marketplace_pedido_stock
from ...utils.cnpj_validator import formatar_cnpj
from ...utils.cpf_validator import CPFValidator

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])
FRETE_FORMATOS_VALIDOS = {"sem_frete", "gratis", "taxa_fixa", "plataforma"}


def _resumo_endereco_cliente_cupom(c: Optional[Cliente]) -> str:
    """Uma linha resumida para cupom: logradouro, cidade/UF, CEP."""
    if not c:
        return ""
    parts: List[str] = []
    end = " ".join((c.endereco or "").split())
    if end:
        parts.append(end)
    cidade = (c.cidade or "").strip()
    uf = (c.uf or "").strip()
    loc = "/".join(x for x in [cidade, uf] if x)
    if loc:
        parts.append(loc)
    cep = " ".join((c.cep or "").split())
    if cep:
        parts.append(f"CEP {cep}")
    return " · ".join(parts)


def _documento_cliente_cupom(c: Optional[Cliente]) -> str:
    if not c:
        return ""
    raw_cnpj = (c.cnpj or "").strip()
    if raw_cnpj:
        return f"CNPJ {formatar_cnpj(raw_cnpj)}"
    raw_cpf = (c.cpf or "").strip()
    if raw_cpf:
        return f"CPF {CPFValidator.formatar_cpf(raw_cpf)}"
    return ""


def _nome_exibicao_pedido_item_marketplace(
    db: Session,
    item: PedidoItemMarketplace,
    nome_por_produto_id: Optional[dict[int, str]] = None,
) -> str:
    """Nome para listagem/cupom: produto do estabelecimento (produto_id) tem prioridade sobre snapshot (título de anúncio)."""
    pid = getattr(item, "produto_id", None)
    if pid is not None:
        pid = int(pid)
        if nome_por_produto_id is not None and pid in nome_por_produto_id:
            return nome_por_produto_id[pid]
        pc = db.query(ProdutoCliente).filter(ProdutoCliente.id == pid).first()
        if pc and (pc.nome or "").strip():
            nome = (pc.nome or "").strip()[:255]
            if nome_por_produto_id is not None:
                nome_por_produto_id[pid] = nome
            return nome
    snap = (getattr(item, "nome_produto_snapshot", None) or "").strip()
    return snap[:255] if snap else "Item"


def _normalize_loja_slug(raw_slug: Optional[str]) -> Optional[str]:
    """Normaliza slug de loja para formato canônico."""
    if raw_slug is None:
        return None
    slug = str(raw_slug).strip()
    if not slug:
        return None
    slug = normalize_slug_or_400(slug, field_name="Slug", max_len=100)
    ensure_slug_not_reserved(slug)
    return slug


def _sync_loja_descricao_campos(update_data: dict) -> None:
    """Mantém `descricao` (legado) alinhada a `descricao_longa` quando uma das duas é enviada."""
    if "descricao_longa" in update_data:
        update_data["descricao"] = update_data.get("descricao_longa")
    elif "descricao" in update_data:
        update_data["descricao_longa"] = update_data.get("descricao")


def _build_slug_categoria_cidade(categoria: Optional[str], cidade: Optional[str]) -> Optional[str]:
    categoria_norm = (categoria or "").strip()
    cidade_norm = (cidade or "").strip()
    if categoria_norm and cidade_norm:
        return f"{categoria_norm}-{cidade_norm}"
    return None


def _sugestoes_vitrine_cliente(db: Session, cliente_id: int) -> dict:
    """Sugestões somente leitura a partir do cadastro do estabelecimento (clientes)."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        return {}
    nome = (cliente.nome or "").strip() or None
    sugestao_cidade = None
    if cliente.cidade and str(cliente.cidade).strip():
        try:
            sugestao_cidade = normalize_city_slug(str(cliente.cidade).strip())
        except HTTPException:
            sugestao_cidade = None
    uf = None
    if cliente.uf and str(cliente.uf).strip():
        u = str(cliente.uf).strip().upper()[:2]
        if len(u) == 2 and u.isalpha():
            uf = u
    sug_nf = nome[:VITRINE_HERO_NOME_FANTASIA_MAX] if nome else None
    return {
        "sugestao_nome_loja": nome,
        "sugestao_nome_fantasia": sug_nf,
        "sugestao_cidade_seo": sugestao_cidade,
        "sugestao_estado_seo": uf,
    }


def _loja_response_com_sugestoes(db: Session, loja: LojaMarketplace) -> LojaMarketplaceResponse:
    base = LojaMarketplaceResponse.model_validate(loja)
    sug = _sugestoes_vitrine_cliente(db, loja.cliente_id)
    return LojaMarketplaceResponse(**{**base.model_dump(), **sug})


def _prepare_loja_seo_fields(update_data: dict) -> dict:
    categoria = update_data.get("categoria_principal")
    cidade = update_data.get("cidade_seo")
    estado = update_data.get("estado_seo")
    if categoria is not None:
        update_data["categoria_principal"] = normalize_category_slug(categoria)
    if cidade is not None:
        update_data["cidade_seo"] = normalize_city_slug(cidade)
    if estado is not None:
        uf = slugify(str(estado)).replace("-", "")
        if not uf or len(uf) != 2:
            raise HTTPException(status_code=400, detail="Estado inválido. Informe UF com 2 letras.")
        update_data["estado_seo"] = uf
    categoria_final = update_data.get("categoria_principal")
    cidade_final = update_data.get("cidade_seo")
    update_data["slug_categoria_cidade"] = _build_slug_categoria_cidade(categoria_final, cidade_final)
    return update_data


def _validar_frete_anuncio(update_data: dict) -> None:
    sobrescrever = update_data.get("frete_sobrescrever_loja")
    formato = update_data.get("formato_frete_produto")
    taxa = update_data.get("taxa_entrega_fixa_produto")
    gratis_apos = update_data.get("entrega_gratis_apos_produto")

    if formato is not None and formato not in FRETE_FORMATOS_VALIDOS:
        raise HTTPException(status_code=400, detail="formato_frete_produto inválido")

    if sobrescrever is False:
        update_data["formato_frete_produto"] = None
        update_data["taxa_entrega_fixa_produto"] = None
        update_data["entrega_gratis_apos_produto"] = None
        return

    if sobrescrever:
        if not formato:
            raise HTTPException(status_code=400, detail="formato_frete_produto obrigatório quando sobrescrever frete da loja")
        if formato in {"taxa_fixa", "plataforma"} and taxa is None:
            raise HTTPException(status_code=400, detail="taxa_entrega_fixa_produto obrigatória para formato_frete_produto taxa_fixa/plataforma")
        if formato in {"sem_frete", "gratis"}:
            update_data["taxa_entrega_fixa_produto"] = None
            update_data["entrega_gratis_apos_produto"] = None
        if formato == "gratis":
            update_data["entrega_gratis_apos_produto"] = None
    elif formato is not None or taxa is not None or gratis_apos is not None:
        raise HTTPException(status_code=400, detail="Defina frete_sobrescrever_loja=true para informar frete do produto")


UPLOAD_LOJA_DIR = "app/static/uploads/loja_marketplace"
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MIME_TO_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


def _salvar_imagem_loja(blob: str, loja_id: int, cliente_id: int, tipo: str) -> str:
    """Salva imagem (logo ou banner) em disco a partir de base64. Retorna path relativo (/static/uploads/...)."""
    if not blob or not blob.strip():
        raise ValueError(f"{tipo}_blob vazio")
    raw = blob.strip()
    m = re.match(r"^data:([^;]+);base64,(.+)$", raw, re.DOTALL)
    if m:
        mime = m.group(1).strip().lower()
        b64 = m.group(2)
        ext = MIME_TO_EXT.get(mime, ".png")
    else:
        b64 = raw
        ext = ".png"
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = ".png"
    try:
        content = base64.b64decode(b64)
    except Exception as e:
        raise ValueError(f"Base64 inválido: {e}")
    if not content:
        raise ValueError("Conteúdo da imagem vazio")
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError("Imagem excede 5 MB. Reduza o tamanho ou resolução.")
    subdir = os.path.join(str(cliente_id), str(loja_id))
    save_dir = os.path.join(UPLOAD_LOJA_DIR, subdir)
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{tipo}_{uuid.uuid4().hex[:12]}{ext}"
    file_path = os.path.join(save_dir, filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return f"/static/uploads/loja_marketplace/{subdir}/{filename}".replace("\\", "/")


def _allowed_cliente_ids(scope: ClienteScope) -> Optional[List[int]]:
    if scope.is_superadmin or scope.see_all:
        return None
    return scope.allowed_ids or []


def _status_pedido_restaura_estoque_marketplace(codigo: str) -> bool:
    """Códigos de status que representam cancelamento e devem devolver estoque (committed/reserved)."""
    c = (codigo or "").strip().lower()
    if not c:
        return False
    if c == "cancelado":
        return True
    if c.startswith("cancelado_"):
        return True
    if c.endswith("_cancelado"):
        return True
    return False


def _status_label_restaura_estoque_marketplace(label: str | None) -> bool:
    """Label configurada no Superadmin (ex.: 'Pedido cancelado') quando o código não segue o padrão cancelado_*."""
    lb = (label or "").strip().lower()
    if not lb:
        return False
    if "não " in lb or "nao " in lb:
        return False
    return "cancelado" in lb or lb.startswith("cancel ")


def _galeria_produto_para_imagens(prod: ProdutoCliente) -> Optional[str]:
    """Monta JSON de lista de URLs de imagens a partir do produto (foto_peca + midias tipo imagem). Padrão marketplaces."""
    urls = []
    if getattr(prod, "foto_peca", None) and str(prod.foto_peca).strip():
        urls.append(prod.foto_peca.strip())
    midias = getattr(prod, "midias", None)
    if midias:
        try:
            data = json.loads(midias) if isinstance(midias, str) else midias
            if isinstance(data, list):
                for m in data:
                    if isinstance(m, dict) and (m.get("tipo") or "").lower() == "imagem" and m.get("url"):
                        urls.append(str(m["url"]).strip())
        except (TypeError, json.JSONDecodeError):
            pass
    return json.dumps(urls) if urls else None


# --- Categorias plataforma (Superadmin ou Admin) ---
@router.get("/categorias", response_model=List[CategoriaPlataformaResponse])
async def listar_categorias_plataforma(
    ativa: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    _: None = Depends(forbid_cliente_access),
):
    """Lista categorias globais da vitrine. Acesso: quem tem marketplace:visualizar (Superadmin, Admin, CA)."""
    q = db.query(CategoriaPlataforma)
    if ativa is not None:
        q = q.filter(CategoriaPlataforma.ativa == ativa)
    rows = q.order_by(CategoriaPlataforma.ordem, CategoriaPlataforma.nome).offset(skip).limit(limit).all()
    return [CategoriaPlataformaResponse.model_validate(r) for r in rows]


@router.post("/categorias", response_model=CategoriaPlataformaResponse, status_code=status.HTTP_201_CREATED)
async def criar_categoria_plataforma(
    body: CategoriaPlataformaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:configurar_loja")),
    _: None = Depends(forbid_cliente_access),
):
    """Cria categoria da plataforma. Uso típico: Superadmin/Admin."""
    if body.slug and db.query(CategoriaPlataforma).filter(CategoriaPlataforma.slug == body.slug).first():
        raise HTTPException(status_code=400, detail="Slug já existe")
    cat = CategoriaPlataforma(
        nome=body.nome,
        slug=body.slug,
        descricao=body.descricao,
        icone=body.icone,
        ordem=body.ordem,
        ativa=body.ativa,
        categoria_pai_id=body.categoria_pai_id,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return CategoriaPlataformaResponse.model_validate(cat)


@router.get("/categorias/{categoria_id}", response_model=CategoriaPlataformaResponse)
async def obter_categoria_plataforma(
    categoria_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
):
    cat = db.query(CategoriaPlataforma).filter(CategoriaPlataforma.id == categoria_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    return CategoriaPlataformaResponse.model_validate(cat)


@router.patch("/categorias/{categoria_id}", response_model=CategoriaPlataformaResponse)
async def atualizar_categoria_plataforma(
    categoria_id: int,
    body: CategoriaPlataformaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:configurar_loja")),
):
    cat = db.query(CategoriaPlataforma).filter(CategoriaPlataforma.id == categoria_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(cat, k, v)
    db.commit()
    db.refresh(cat)
    return CategoriaPlataformaResponse.model_validate(cat)


# --- Loja do CA ---
@router.get("/lojas", response_model=dict, dependencies=[Depends(require_superadmin())])
async def listar_lojas_superadmin(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(200, ge=1, le=500),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Lista todas as lojas marketplace (SuperAdmin only). Usado na página de áreas de entrega."""
    q = db.query(LojaMarketplace)
    if status_filter:
        q = q.filter(LojaMarketplace.status == status_filter)
    total = q.count()
    rows = q.order_by(LojaMarketplace.id).offset(skip).limit(limit).all()
    items = [LojaMarketplaceResponse.model_validate(r) for r in rows]
    return {"items": [i.model_dump() for i in items], "total": total}


@router.get("/loja", response_model=Optional[LojaMarketplaceResponse])
async def obter_minha_loja(
    cliente_id: int = Query(..., description="Estabelecimento (clientes.id)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Retorna a loja marketplace do estabelecimento, se existir. Escopo: cliente_id deve estar no escopo do usuário."""
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.cliente_id == cliente_id).first()
    if not loja:
        return None
    return _loja_response_com_sugestoes(db, loja)


@router.post("/loja", response_model=LojaMarketplaceResponse, status_code=status.HTTP_201_CREATED)
async def ativar_loja(
    body: LojaMarketplaceCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:configurar_loja")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Ativa/cria a loja marketplace do estabelecimento. Escopo: cliente_id no escopo."""
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and body.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
    existente = db.query(LojaMarketplace).filter(LojaMarketplace.cliente_id == body.cliente_id).first()
    if existente:
        raise HTTPException(status_code=400, detail="Loja já existe para este estabelecimento")
    slug_norm = _normalize_loja_slug(body.slug) if body.slug else None
    if slug_norm:
        slug_norm = generate_unique_slug(db, LojaMarketplace, slug_norm, field_name="slug")
    payload = _prepare_loja_seo_fields(body.model_dump())
    nome_f = payload.get("nome_fantasia") or payload.get("nome_loja")
    desc_long = payload.get("descricao_longa") or payload.get("descricao")
    loja = LojaMarketplace(
        cliente_id=body.cliente_id,
        status="ativo",  # loja ativa para aparecer na vitrine
        slug=slug_norm,
        nome_loja=payload.get("nome_loja"),
        nome_fantasia=nome_f,
        categoria_principal=payload.get("categoria_principal"),
        subcategoria=payload.get("subcategoria"),
        cidade_seo=payload.get("cidade_seo"),
        estado_seo=payload.get("estado_seo"),
        slug_categoria_cidade=payload.get("slug_categoria_cidade"),
        seo_title=payload.get("seo_title"),
        seo_description=payload.get("seo_description"),
        og_image_url=payload.get("og_image_url"),
        seo_enabled=payload.get("seo_enabled", True),
        descricao=payload.get("descricao") or desc_long,
        descricao_curta=payload.get("descricao_curta"),
        descricao_longa=desc_long,
        vitrine_hero_titulo_uma_linha=bool(payload.get("vitrine_hero_titulo_uma_linha", False)),
        logo_url=payload.get("logo_url"),
        banner_url=payload.get("banner_url"),
        tipo_entrega=payload.get("tipo_entrega"),
        raio_entrega_km=payload.get("raio_entrega_km"),
        taxa_entrega_fixa=payload.get("taxa_entrega_fixa"),
        entrega_gratis_apos=payload.get("entrega_gratis_apos"),
    )
    db.add(loja)
    db.commit()
    db.refresh(loja)
    return _loja_response_com_sugestoes(db, loja)


@router.patch("/loja/{loja_id}", response_model=LojaMarketplaceResponse)
async def atualizar_loja(
    loja_id: int,
    body: LojaMarketplaceUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:configurar_loja")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == loja_id).first()
    if not loja:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and loja.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Loja fora do escopo")
    update_data = body.model_dump(exclude_unset=True)
    _sync_loja_descricao_campos(update_data)
    update_data = _prepare_loja_seo_fields(update_data)
    if "categoria_principal" in update_data or "cidade_seo" in update_data:
        categoria_merged = update_data.get("categoria_principal", loja.categoria_principal)
        cidade_merged = update_data.get("cidade_seo", loja.cidade_seo)
        update_data["slug_categoria_cidade"] = _build_slug_categoria_cidade(categoria_merged, cidade_merged)
    campos_seo_restritos = {"seo_title", "seo_description", "og_image_url", "seo_enabled"}
    if any(c in update_data for c in campos_seo_restritos):
        if not current_user.role or current_user.role.nome != "Superadministrador":
            raise HTTPException(status_code=403, detail="Apenas Superadministrador pode alterar SEO avançado da loja")
    if "slug" in update_data:
        slug_norm = _normalize_loja_slug(update_data.get("slug"))
        slug_atual = _normalize_loja_slug(loja.slug)
        if slug_norm != slug_atual:
            if slug_atual:
                hist_exists = db.query(LojaSlugHistory).filter(
                    func.lower(LojaSlugHistory.slug_antigo) == slug_atual
                ).first()
                if not hist_exists:
                    db.add(LojaSlugHistory(loja_id=loja.id, slug_antigo=slug_atual))
            if slug_norm:
                slug_norm = generate_unique_slug(
                    db,
                    LojaMarketplace,
                    slug_norm,
                    field_name="slug",
                    exclude_id=loja.id,
                )
        update_data["slug"] = slug_norm
    campos_frete_restritos = {"formato_frete", "taxa_entrega_fixa", "entrega_gratis_apos"}
    if any(c in update_data for c in campos_frete_restritos):
        if not current_user.role or current_user.role.nome != "Superadministrador":
            raise HTTPException(status_code=403, detail="Apenas Superadministrador pode alterar formato de frete da loja")
    logo_blob = update_data.pop("logo_blob", None)
    banner_blob = update_data.pop("banner_blob", None)
    if logo_blob:
        try:
            update_data["logo_url"] = _salvar_imagem_loja(logo_blob, loja_id, loja.cliente_id, "logo")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if banner_blob:
        try:
            update_data["banner_url"] = _salvar_imagem_loja(banner_blob, loja_id, loja.cliente_id, "banner")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    for k, v in update_data.items():
        setattr(loja, k, v)
    db.commit()
    db.refresh(loja)
    return _loja_response_com_sugestoes(db, loja)


@router.get("/taxas-vigentes", response_model=MarketplaceTaxasVigentesResponse)
async def marketplace_taxas_vigentes(
    cliente_id: int = Query(..., description="Estabelecimento (clientes.id)"),
    preco: Optional[Decimal] = Query(
        None,
        description="Preço de referência para calcular preview (opcional); ex.: preço promocional ou original.",
    ),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Regra de taxas aplicável ao tenant do usuário + preview opcional por preço."""
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
    tid = getattr(current_user, "tenant_id", None)
    if tid is None:
        raise HTTPException(
            status_code=400,
            detail="Usuário sem tenant_id: não é possível resolver taxas marketplace.",
        )
    try:
        row, escopo_aplicado, payload = resolver_regra_e_payload(db, int(tid))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    preview = None
    if preco is not None:
        try:
            preview = montar_preview(payload, preco)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return MarketplaceTaxasVigentesResponse(
        regra_id=row.id,
        nome_regra=row.nome,
        escopo_aplicado=escopo_aplicado,
        payload=payload,
        preview=preview,
    )


# --- Anúncios ---
@router.get("/anuncios", response_model=dict)
async def listar_anuncios(
    loja_id: Optional[int] = Query(None),
    cliente_id: Optional[int] = Query(None, description="Estabelecimento; usado para filtrar por loja do cliente"),
    status_: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista anúncios da loja. Escopo: loja/cliente no escopo do usuário."""
    q = db.query(AnuncioPlataforma).join(LojaMarketplace)
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None:
        q = q.filter(LojaMarketplace.cliente_id.in_(allowed))
    if loja_id is not None:
        q = q.filter(AnuncioPlataforma.loja_id == loja_id)
    if cliente_id is not None:
        if allowed is not None and cliente_id not in allowed:
            raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
        q = q.filter(LojaMarketplace.cliente_id == cliente_id)
    if status_ is not None:
        q = q.filter(AnuncioPlataforma.status == status_)
    total = q.count()
    rows = q.order_by(AnuncioPlataforma.updated_at.desc()).offset(skip).limit(limit).all()
    return {
        "items": [AnuncioPlataformaResponse.model_validate(r) for r in rows],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("/anuncios", response_model=AnuncioPlataformaResponse, status_code=status.HTTP_201_CREATED)
async def criar_anuncio(
    body: AnuncioPlataformaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:publicar")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == body.loja_id).first()
    if not loja:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and loja.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Loja fora do escopo")
    prod = db.query(ProdutoCliente).filter(
        ProdutoCliente.id == body.produto_ca_id,
        ProdutoCliente.cliente_id == loja.cliente_id,
    ).first()
    if not prod:
        raise HTTPException(status_code=400, detail="Produto não pertence ao estabelecimento da loja")
    existente = db.query(AnuncioPlataforma).filter(
        AnuncioPlataforma.loja_id == body.loja_id,
        AnuncioPlataforma.produto_ca_id == body.produto_ca_id,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="Este produto já está anunciado nesta loja")
    imagens_anuncio = body.imagens
    if not imagens_anuncio or (isinstance(imagens_anuncio, str) and not imagens_anuncio.strip()):
        imagens_anuncio = _galeria_produto_para_imagens(prod)
    anuncio_data = body.model_dump()
    _validar_frete_anuncio(anuncio_data)
    anuncio = AnuncioPlataforma(
        loja_id=body.loja_id,
        produto_ca_id=body.produto_ca_id,
        categoria_id=body.categoria_id,
        status="publicado",  # publicado para aparecer na vitrine ao criar
        titulo=body.titulo,
        descricao=body.descricao,
        imagens=imagens_anuncio,
        preco_original=body.preco_original,
        preco_promocional=body.preco_promocional,
        tipo_estoque=body.tipo_estoque,
        estoque_atual=prod.quantidade_atual if body.tipo_estoque == "sincronizado" else None,
        estoque_minimo_alerta=body.estoque_minimo_alerta,
        atributos=body.atributos,
        frete_sobrescrever_loja=anuncio_data.get("frete_sobrescrever_loja", False),
        formato_frete_produto=anuncio_data.get("formato_frete_produto"),
        taxa_entrega_fixa_produto=anuncio_data.get("taxa_entrega_fixa_produto"),
        entrega_gratis_apos_produto=anuncio_data.get("entrega_gratis_apos_produto"),
        og_image_url=(anuncio_data.get("og_image_url") or "").strip() or None,
        custo_plataforma_estimado=anuncio_data.get("custo_plataforma_estimado"),
        custo_cartao_estimado=anuncio_data.get("custo_cartao_estimado"),
    )
    db.add(anuncio)
    # Garantir que a loja esteja ativa para aparecer na vitrine quando há anúncio publicado
    if loja.status == "pendente":
        loja.status = "ativo"
    db.commit()
    db.refresh(anuncio)
    return AnuncioPlataformaResponse.model_validate(anuncio)


@router.get("/anuncios/{anuncio_id}", response_model=AnuncioPlataformaResponse)
async def obter_anuncio(
    anuncio_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    anuncio = db.query(AnuncioPlataforma).filter(AnuncioPlataforma.id == anuncio_id).first()
    if not anuncio:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None:
        loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == anuncio.loja_id).first()
        if not loja or loja.cliente_id not in allowed:
            raise HTTPException(status_code=403, detail="Anúncio fora do escopo")
    return AnuncioPlataformaResponse.model_validate(anuncio)


@router.patch("/anuncios/{anuncio_id}", response_model=AnuncioPlataformaResponse)
async def atualizar_anuncio(
    anuncio_id: int,
    body: AnuncioPlataformaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:publicar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    anuncio = db.query(AnuncioPlataforma).filter(AnuncioPlataforma.id == anuncio_id).first()
    if not anuncio:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None:
        loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == anuncio.loja_id).first()
        if not loja or loja.cliente_id not in allowed:
            raise HTTPException(status_code=403, detail="Anúncio fora do escopo")
    dump = body.model_dump(exclude_unset=True)
    _validar_frete_anuncio(dump)
    if "imagens" not in dump and anuncio.produto_ca_id:
        prod = db.query(ProdutoCliente).filter(ProdutoCliente.id == anuncio.produto_ca_id).first()
        if prod:
            anuncio.imagens = _galeria_produto_para_imagens(prod)
    for k, v in dump.items():
        setattr(anuncio, k, v)
    # Ao publicar anúncio, ativar a loja se estiver pendente para aparecer na vitrine
    if dump.get("status") == "publicado":
        loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == anuncio.loja_id).first()
        if loja and loja.status == "pendente":
            loja.status = "ativo"
    db.commit()
    db.refresh(anuncio)
    return AnuncioPlataformaResponse.model_validate(anuncio)


# --- Sincronização de estoque ---
@router.post("/sync/estoque")
async def sincronizar_estoque(
    loja_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:publicar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Sincroniza estoque dos anúncios a partir de produtos_cliente (tipo_estoque = sincronizado). Registra em SyncControle."""
    from datetime import datetime, timezone

    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == loja_id).first()
    if not loja:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and loja.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Loja fora do escopo")

    sync = SyncControle(
        loja_id=loja_id,
        tipo_sync="estoque",
        status="em_andamento",
        iniciado_em=datetime.now(timezone.utc),
    )
    db.add(sync)
    db.flush()

    anuncios = db.query(AnuncioPlataforma).filter(
        AnuncioPlataforma.loja_id == loja_id,
        AnuncioPlataforma.tipo_estoque == "sincronizado",
    ).all()
    erros = []
    for a in anuncios:
        prod = db.query(ProdutoCliente).filter(ProdutoCliente.id == a.produto_ca_id).first()
        if prod is not None:
            a.estoque_atual = prod.quantidade_atual
            a.ultima_sincronizacao = datetime.now(timezone.utc)
        else:
            erros.append(f"Produto {a.produto_ca_id} não encontrado para anúncio {a.id}")

    sync.status = "concluido"
    sync.finalizado_em = datetime.now(timezone.utc)
    sync.dados_resumo = f"anuncios_sincronizados={len(anuncios)}"
    if erros:
        sync.log_erros = "\n".join(erros[:20])

    db.commit()
    return {"sincronizados": len(anuncios), "loja_id": loja_id, "sync_controle_id": sync.id}


# --- Status pedido marketplace (configurável Super Admin; CA lê lista ativa) ---
@router.get("/status-pedido", response_model=List[StatusPedidoMarketplaceResponse])
async def listar_status_pedido_marketplace(
    incluir_inativos: bool = Query(False, description="Se True, retorna todos (apenas Super Admin)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista status de pedido da loja. Sem incluir_inativos: apenas ativos (CA usa para filtro e modal). Com incluir_inativos=true: todos (apenas Super Admin)."""
    if incluir_inativos and not scope.is_superadmin:
        raise HTTPException(status_code=403, detail="Apenas Superadministrador pode listar status inativos")
    q = db.query(StatusPedidoMarketplace)
    if not incluir_inativos:
        q = q.filter(StatusPedidoMarketplace.ativo.is_(True))
    rows = q.order_by(StatusPedidoMarketplace.ordem, StatusPedidoMarketplace.codigo).all()
    return [StatusPedidoMarketplaceResponse.model_validate(r) for r in rows]


@router.post("/status-pedido", response_model=StatusPedidoMarketplaceResponse, status_code=status.HTTP_201_CREATED)
async def criar_status_pedido_marketplace(
    body: StatusPedidoMarketplaceCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_superadmin()),
):
    """Cria status de pedido da loja. Apenas Super Admin."""
    existente = db.query(StatusPedidoMarketplace).filter(StatusPedidoMarketplace.codigo == body.codigo).first()
    if existente:
        raise HTTPException(status_code=400, detail="Já existe um status com este código")
    row = StatusPedidoMarketplace(
        codigo=body.codigo.strip(),
        label=body.label.strip(),
        ordem=body.ordem,
        ativo=body.ativo,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return StatusPedidoMarketplaceResponse.model_validate(row)


@router.patch("/status-pedido/{status_id}", response_model=StatusPedidoMarketplaceResponse)
async def atualizar_status_pedido_marketplace(
    status_id: int,
    body: StatusPedidoMarketplaceUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_superadmin()),
):
    """Atualiza status de pedido da loja. Apenas Super Admin."""
    row = db.query(StatusPedidoMarketplace).filter(StatusPedidoMarketplace.id == status_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Status não encontrado")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return StatusPedidoMarketplaceResponse.model_validate(row)


@router.patch("/status-pedido/{status_id}/desativar", response_model=StatusPedidoMarketplaceResponse)
async def desativar_status_pedido_marketplace(
    status_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_superadmin()),
):
    """Desativa status (ativo=false). Apenas Super Admin. Pedidos já com este código continuam exibindo-o."""
    row = db.query(StatusPedidoMarketplace).filter(StatusPedidoMarketplace.id == status_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Status não encontrado")
    row.ativo = False
    db.commit()
    db.refresh(row)
    return StatusPedidoMarketplaceResponse.model_validate(row)


# --- Pedidos da loja (CA gerencia) ---
@router.get("/loja/{loja_id}/pedidos", response_model=dict)
async def listar_pedidos_loja(
    loja_id: int,
    status_pedido: Optional[str] = Query(None),
    status_pagamento: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:gerenciar_pedidos")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista pedidos da loja. Escopo: loja deve pertencer ao estabelecimento do usuário."""
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == loja_id).first()
    if not loja:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and loja.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Loja fora do escopo")
    q = db.query(PedidoMarketplace).filter(PedidoMarketplace.loja_id == loja_id)
    if status_pedido:
        q = q.filter(PedidoMarketplace.status_pedido == status_pedido)
    if status_pagamento:
        q = q.filter(PedidoMarketplace.status_pagamento == status_pagamento)
    total = q.count()
    pedidos = q.order_by(PedidoMarketplace.created_at.desc()).offset(skip).limit(limit).all()
    pedido_itens_rows: list[tuple] = []
    produto_ids: set[int] = set()
    for p in pedidos:
        itens = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == p.id).all()
        pedido_itens_rows.append((p, itens))
        for i in itens:
            pid = getattr(i, "produto_id", None)
            if pid is not None:
                produto_ids.add(int(pid))
    nome_por_produto: dict[int, str] = {}
    if produto_ids:
        for pc in db.query(ProdutoCliente).filter(ProdutoCliente.id.in_(produto_ids)).all():
            if pc.nome and str(pc.nome).strip():
                nome_por_produto[pc.id] = str(pc.nome).strip()[:255]
    items = []
    for p, itens in pedido_itens_rows:
        gestao_itens = [
            PedidoItemGestaoResponse(
                id=i.id,
                anuncio_id=i.anuncio_id,
                nome_produto_snapshot=_nome_exibicao_pedido_item_marketplace(db, i, nome_por_produto),
                quantidade=int(i.quantidade),
                preco_unitario=i.preco_unitario,
                preco_total=i.preco_total,
            )
            for i in itens
        ]
        items.append(
            PedidoMarketplaceResponse(
                id=p.id,
                numero_pedido=getattr(p, "numero_pedido", "") or f"{getattr(p, 'tenant_id', '')}-{p.id}",
                loja_id=p.loja_id,
                comprador_id=p.comprador_id,
                comprador_nome=p.comprador_nome or "",
                comprador_email=p.comprador_email,
                comprador_telefone=p.comprador_telefone,
                destinatario_nome=getattr(p, "destinatario_nome", None),
                subtotal=p.subtotal,
                desconto=p.desconto,
                taxa_entrega=p.taxa_entrega,
                total=p.total,
                status_pedido=p.status_pedido or "",
                status_pagamento=p.status_pagamento or "",
                status_entrega=getattr(p, "status_entrega", "") or "pendente",
                endereco_entrega=p.endereco_entrega,
                tipo_entrega=p.tipo_entrega or "retirada",
                created_at=p.created_at,
                itens=gestao_itens,
            )
        )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/pedidos/{pedido_id}/cupom", response_model=CupomConteudoResponse)
async def obter_cupom_pedido_marketplace(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:gerenciar_pedidos")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Conteúdo do cupom não fiscal do pedido marketplace para impressão."""
    ped = (
        db.query(PedidoMarketplace)
        .options(
            joinedload(PedidoMarketplace.itens),
            joinedload(PedidoMarketplace.loja).joinedload(LojaMarketplace.cliente),
        )
        .filter(PedidoMarketplace.id == pedido_id)
        .first()
    )
    if not ped:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    loja = ped.loja if getattr(ped, "loja", None) else db.query(LojaMarketplace).filter(LojaMarketplace.id == ped.loja_id).first()
    if not loja:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and loja.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Pedido fora do escopo")
    tenant_id = getattr(current_user, "tenant_id", None)
    tenant = db.get(Tenant, tenant_id) if tenant_id else None
    cupom_tipo = "nao_fiscal"
    if tenant and getattr(tenant, "cupom_tipo", None) == "fiscal":
        cupom_tipo = "fiscal"
    if cupom_tipo == "fiscal":
        return CupomConteudoResponse(tipo="fiscal", linhas=[], html=None)
    nome_loja = (loja.nome_loja or loja.nome_fantasia or "").strip()
    if not nome_loja and loja.cliente and (loja.cliente.nome or "").strip():
        nome_loja = (loja.cliente.nome or "").strip()
    if not nome_loja:
        nome_loja = "Loja"
    cli = loja.cliente
    loja_endereco_resumo = _resumo_endereco_cliente_cupom(cli)
    loja_documento = _documento_cliente_cupom(cli)
    itens_data = []
    nome_cache_cupom: dict[int, str] = {}
    for i in ped.itens or []:
        nome = _nome_exibicao_pedido_item_marketplace(db, i, nome_cache_cupom)
        itens_data.append(
            {
                "nome_produto_snapshot": nome,
                "quantidade": int(i.quantidade),
                "preco_unitario": float(i.preco_unitario),
                "preco_total": float(i.preco_total),
            }
        )
    linhas, html = gerar_cupom_resumo_pedido_marketplace(
        loja_exibicao=nome_loja,
        numero_pedido=ped.numero_pedido or "",
        data_referencia=ped.created_at,
        comprador_nome=ped.comprador_nome or "",
        comprador_telefone=ped.comprador_telefone,
        destinatario_nome=getattr(ped, "destinatario_nome", None),
        tipo_entrega=ped.tipo_entrega or "retirada",
        endereco_entrega=ped.endereco_entrega,
        status_pedido=ped.status_pedido or "",
        status_pagamento=ped.status_pagamento or "",
        subtotal=ped.subtotal,
        desconto=ped.desconto,
        taxa_entrega=ped.taxa_entrega,
        total=ped.total,
        itens=itens_data,
        loja_endereco_resumo=loja_endereco_resumo or None,
        loja_documento=loja_documento or None,
    )
    return CupomConteudoResponse(tipo="nao_fiscal", linhas=linhas, html=html)



@router.patch("/pedidos/{pedido_id}", response_model=PedidoMarketplaceResponse)
async def atualizar_pedido_loja(
    pedido_id: int,
    body: PedidoMarketplaceUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:gerenciar_pedidos")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Atualiza status do pedido (status_pedido, status_pagamento). Escopo: pedido da sua loja."""
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == pedido.loja_id).first()
    if not loja:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and loja.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Pedido fora do escopo")
    if body.status_pedido is not None and str(body.status_pedido).strip():
        status_codigo = str(body.status_pedido).strip()
        st = db.query(StatusPedidoMarketplace).filter(
            StatusPedidoMarketplace.codigo == status_codigo,
            StatusPedidoMarketplace.ativo.is_(True),
        ).first()
        if not st:
            raise HTTPException(
                status_code=400,
                detail=f"Status de pedido '{status_codigo}' não existe ou está inativo. Use um status configurado pelo administrador.",
            )
    status_anterior = pedido.status_pedido
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(pedido, k, v)
    status_label_evt = None
    if (
        body.status_pedido is not None
        and str(body.status_pedido).strip()
        and (status_anterior or "") != (pedido.status_pedido or "")
    ):
        novo_status = str(pedido.status_pedido or "").strip()
        st = db.query(StatusPedidoMarketplace).filter(
            StatusPedidoMarketplace.codigo == novo_status,
            StatusPedidoMarketplace.ativo.is_(True),
        ).first()
        status_label_evt = st.label if st else novo_status.replace("_", " ").title()
        registrar_pedido_status_evento(
            db,
            pedido_id=pedido.id,
            tipo_evento="status_alterado",
            status_codigo=novo_status,
            status_label=status_label_evt,
            actor_type="loja",
            actor_id=current_user.id,
        )
    deve_restaurar_estoque = False
    if body.status_pedido is not None and str(body.status_pedido).strip():
        codigo_aplicado = str(pedido.status_pedido or "").strip()
        st_row = (
            db.query(StatusPedidoMarketplace)
            .filter(StatusPedidoMarketplace.codigo == codigo_aplicado)
            .first()
        )
        lbl = (st_row.label if st_row else "") or ""
        if _status_pedido_restaura_estoque_marketplace(codigo_aplicado) or _status_label_restaura_estoque_marketplace(
            lbl
        ):
            deve_restaurar_estoque = True
    if not deve_restaurar_estoque and body.status_pagamento is not None and str(body.status_pagamento).strip():
        if str(body.status_pagamento).strip().lower() == "estornado":
            deve_restaurar_estoque = True
    if deve_restaurar_estoque:
        restore_marketplace_pedido_stock(db, pedido.id)
        db.flush()
    db.commit()
    db.refresh(pedido)
    # Real-time para o comprador (consumidor). Best-effort.
    if status_label_evt and getattr(pedido, "comprador_id", None):
        try:
            publish_consumidor_event(
                int(pedido.comprador_id),
                "pedido.status_alterado",
                {
                    "pedido_id": pedido.id,
                    "status_codigo": (pedido.status_pedido or "").strip(),
                    "status_label": status_label_evt,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception:
            pass
    if status_label_evt:
        try:
            from app.worker.tasks import notificar_marketplace_pedido_status_email_comprador

            notificar_marketplace_pedido_status_email_comprador.delay(
                pedido.id,
                status_anterior or "",
                (pedido.status_pedido or "").strip(),
                status_label_evt,
            )
        except Exception:
            pass
    itens = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == pedido.id).all()
    produto_ids_patch = {int(i.produto_id) for i in itens if getattr(i, "produto_id", None) is not None}
    nome_por_patch: dict[int, str] = {}
    if produto_ids_patch:
        for pc in db.query(ProdutoCliente).filter(ProdutoCliente.id.in_(produto_ids_patch)).all():
            if pc.nome and str(pc.nome).strip():
                nome_por_patch[pc.id] = str(pc.nome).strip()[:255]
    gestao_itens_patch = [
        PedidoItemGestaoResponse(
            id=i.id,
            anuncio_id=i.anuncio_id,
            nome_produto_snapshot=_nome_exibicao_pedido_item_marketplace(db, i, nome_por_patch),
            quantidade=int(i.quantidade),
            preco_unitario=i.preco_unitario,
            preco_total=i.preco_total,
        )
        for i in itens
    ]
    return PedidoMarketplaceResponse(
        id=pedido.id,
        numero_pedido=getattr(pedido, "numero_pedido", "") or f"{getattr(pedido, 'tenant_id', '')}-{pedido.id}",
        loja_id=pedido.loja_id,
        comprador_id=pedido.comprador_id,
        comprador_nome=pedido.comprador_nome or "",
        comprador_email=pedido.comprador_email,
        comprador_telefone=pedido.comprador_telefone,
        destinatario_nome=getattr(pedido, "destinatario_nome", None),
        subtotal=pedido.subtotal,
        desconto=pedido.desconto,
        taxa_entrega=pedido.taxa_entrega,
        total=pedido.total,
        status_pedido=pedido.status_pedido or "",
        status_pagamento=pedido.status_pagamento or "",
        status_entrega=getattr(pedido, "status_entrega", "") or "pendente",
        endereco_entrega=pedido.endereco_entrega,
        tipo_entrega=pedido.tipo_entrega or "retirada",
        created_at=pedido.created_at,
        itens=gestao_itens_patch,
    )


# --- Extrato da loja (financeiro) ---
@router.get("/loja/{loja_id}/extrato", response_model=List[ExtratoLojaResponse])
async def listar_extrato_loja(
    loja_id: int,
    tipo: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:financeiro")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista extrato financeiro da loja. Escopo: loja do estabelecimento do usuário."""
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == loja_id).first()
    if not loja:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and loja.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Loja fora do escopo")
    q = db.query(ExtratoLoja).filter(ExtratoLoja.loja_id == loja_id)
    if tipo:
        q = q.filter(ExtratoLoja.tipo == tipo)
    rows = q.order_by(ExtratoLoja.created_at.desc()).offset(skip).limit(limit).all()
    return [ExtratoLojaResponse.model_validate(r) for r in rows]


# --- Consumidores (gestão por tenant/loja) ---
@router.get("/consumidores", response_model=dict)
async def listar_consumidores_marketplace(
    tenant_id: Optional[int] = Query(None, description="clientes.id do estabelecimento"),
    tipo_consumidor: Optional[str] = Query(None),
    status_cadastro: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista consumidores do marketplace. Escopo: tenant_id deve estar no escopo do usuário."""
    allowed = _allowed_cliente_ids(scope)
    if tenant_id is not None and allowed is not None and tenant_id not in allowed:
        raise HTTPException(status_code=403, detail="Tenant fora do escopo")
    q = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.deleted_at.is_(None))
    if tenant_id is not None:
        q = q.filter(ConsumidorMarketplace.tenant_id == tenant_id)
    elif allowed is not None:
        q = q.filter(ConsumidorMarketplace.tenant_id.in_(allowed))
    if tipo_consumidor:
        q = q.filter(ConsumidorMarketplace.tipo_consumidor == tipo_consumidor)
    if status_cadastro:
        q = q.filter(ConsumidorMarketplace.status_cadastro == status_cadastro)
    total = q.count()
    rows = q.order_by(ConsumidorMarketplace.id.desc()).offset(skip).limit(limit).all()
    items = [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "email": r.email,
            "nome": r.nome,
            "telefone": r.telefone,
            "tipo_consumidor": r.tipo_consumidor or "",
            "status_cadastro": r.status_cadastro or "",
            "aceite_marketing": getattr(r, "aceite_marketing", False),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


# --- Eventos de integração (gestão por tenant) ---
@router.get("/integracao/eventos", response_model=dict)
async def listar_eventos_integracao(
    tenant_id: Optional[int] = Query(None, description="clientes.id do estabelecimento"),
    event_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista eventos de integração CRM. Escopo: tenant_id no escopo do usuário."""
    allowed = _allowed_cliente_ids(scope)
    if tenant_id is not None and allowed is not None and tenant_id not in allowed:
        raise HTTPException(status_code=403, detail="Tenant fora do escopo")
    q = db.query(IntegrationEvent)
    if tenant_id is not None:
        q = q.filter(IntegrationEvent.tenant_id == tenant_id)
    elif allowed is not None:
        q = q.filter(IntegrationEvent.tenant_id.in_(allowed))
    if event_name:
        q = q.filter(IntegrationEvent.event_name == event_name)
    if status:
        q = q.filter(IntegrationEvent.status == status)
    total = q.count()
    rows = q.order_by(IntegrationEvent.id.desc()).offset(skip).limit(limit).all()
    items = [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "event_name": r.event_name,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "payload_json": dict(r.payload_json) if r.payload_json else {},
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


# ────────────────────────────────────────────────────────────────────────────
# CRUD Áreas de Entrega
# SuperAdmin: full CRUD. CA (Cliente Administrador): apenas visualizar áreas da própria loja.
# ────────────────────────────────────────────────────────────────────────────

@router.get(
    "/minha-loja/areas-entrega",
    response_model=List[LojaAreaEntregaResponse],
)
async def listar_minha_loja_areas_entrega(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista áreas de entrega da loja do CA (read-only). Usado quando o usuário não é SuperAdmin."""
    if scope.is_superadmin:
        return []
    allowed = scope.allowed_ids or []
    for cliente_id in allowed:
        loja = db.query(LojaMarketplace).filter(LojaMarketplace.cliente_id == cliente_id).first()
        if loja:
            rows = (
                db.query(LojaAreaEntrega)
                .filter(LojaAreaEntrega.loja_id == loja.id)
                .order_by(LojaAreaEntrega.cidade)
                .all()
            )
            return [LojaAreaEntregaResponse.model_validate(r) for r in rows]
    return []


@router.get(
    "/loja/{loja_id}/areas-entrega",
    response_model=List[LojaAreaEntregaResponse],
)
def listar_areas_entrega(
    loja_id: int,
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista áreas de entrega. SuperAdmin: qualquer loja. CA/Admin: apenas loja no escopo."""
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == loja_id).first()
    if not loja:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    if not scope.is_superadmin and not scope.see_all:
        allowed = _allowed_cliente_ids(scope)
        if allowed is not None and loja.cliente_id not in allowed:
            raise HTTPException(status_code=403, detail="Loja fora do escopo")
    q = db.query(LojaAreaEntrega).filter(LojaAreaEntrega.loja_id == loja_id)
    if ativo is not None:
        q = q.filter(LojaAreaEntrega.ativo == ativo)
    return q.order_by(LojaAreaEntrega.cidade).all()


@router.post(
    "/loja/{loja_id}/areas-entrega",
    response_model=LojaAreaEntregaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_superadmin())],
)
def criar_area_entrega(
    loja_id: int,
    body: LojaAreaEntregaCreate,
    db: Session = Depends(get_db),
):
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == loja_id).first()
    if not loja:
        raise HTTPException(404, "Loja não encontrada")
    existing = db.query(LojaAreaEntrega).filter(
        LojaAreaEntrega.loja_id == loja_id,
        LojaAreaEntrega.cidade == body.cidade.strip(),
        LojaAreaEntrega.uf == body.uf.strip().upper(),
    ).first()
    if existing:
        raise HTTPException(409, f"Cidade {body.cidade}-{body.uf} já cadastrada para esta loja")
    area = LojaAreaEntrega(
        loja_id=loja_id,
        cidade=body.cidade.strip(),
        uf=body.uf.strip().upper(),
        codigo_ibge=body.codigo_ibge,
        taxa_entrega=body.taxa_entrega,
        prazo_dias=body.prazo_dias,
    )
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


@router.patch(
    "/areas-entrega/{area_id}",
    response_model=LojaAreaEntregaResponse,
    dependencies=[Depends(require_superadmin())],
)
def atualizar_area_entrega(
    area_id: int,
    body: LojaAreaEntregaUpdate,
    db: Session = Depends(get_db),
):
    area = db.query(LojaAreaEntrega).filter(LojaAreaEntrega.id == area_id).first()
    if not area:
        raise HTTPException(404, "Área de entrega não encontrada")
    for field, val in body.model_dump(exclude_unset=True).items():
        if field == "uf" and val is not None:
            val = val.strip().upper()
        if field == "cidade" and val is not None:
            val = val.strip()
        setattr(area, field, val)
    db.commit()
    db.refresh(area)
    return area


@router.delete(
    "/areas-entrega/{area_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_superadmin())],
)
def remover_area_entrega(
    area_id: int,
    db: Session = Depends(get_db),
):
    area = db.query(LojaAreaEntrega).filter(LojaAreaEntrega.id == area_id).first()
    if not area:
        raise HTTPException(404, "Área de entrega não encontrada")
    db.delete(area)
    db.commit()


# ─── Admin: App Version Control ─────────────────────────────
@router.get(
    "/app-versao/{plataforma}",
    dependencies=[Depends(require_superadmin())],
)
def admin_get_app_versao(
    plataforma: str,
    db: Session = Depends(get_db),
):
    from ...models.app_versao_config import AppVersaoConfig
    config = db.query(AppVersaoConfig).filter(AppVersaoConfig.plataforma == plataforma.lower()).first()
    if not config:
        raise HTTPException(404, f"Plataforma '{plataforma}' não encontrada")
    return {
        "plataforma": config.plataforma,
        "versao_minima": config.versao_minima,
        "versao_recomendada": config.versao_recomendada,
        "url_loja": config.url_loja,
        "mensagem": config.mensagem,
    }


@router.patch(
    "/app-versao/{plataforma}",
    dependencies=[Depends(require_superadmin())],
)
def admin_update_app_versao(
    plataforma: str,
    body: dict,
    db: Session = Depends(get_db),
):
    from ...models.app_versao_config import AppVersaoConfig
    from ...schemas.mobile import AppVersionUpdateRequest

    parsed = AppVersionUpdateRequest(**body)
    config = db.query(AppVersaoConfig).filter(AppVersaoConfig.plataforma == plataforma.lower()).first()
    if not config:
        raise HTTPException(404, f"Plataforma '{plataforma}' não encontrada")
    if parsed.versao_minima is not None:
        config.versao_minima = parsed.versao_minima
    if parsed.versao_recomendada is not None:
        config.versao_recomendada = parsed.versao_recomendada
    if parsed.url_loja is not None:
        config.url_loja = parsed.url_loja
    if parsed.mensagem is not None:
        config.mensagem = parsed.mensagem
    db.commit()
    db.refresh(config)
    return {
        "plataforma": config.plataforma,
        "versao_minima": config.versao_minima,
        "versao_recomendada": config.versao_recomendada,
        "url_loja": config.url_loja,
        "mensagem": config.mensagem,
    }


# ─── Admin: CRUD Cupons ─────────────────────────────────────
@router.get(
    "/cupons",
    dependencies=[Depends(require_superadmin())],
)
def admin_listar_cupons(
    ativo: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    from ...models.cupom_marketplace import CupomMarketplace
    q = db.query(CupomMarketplace)
    if ativo is not None:
        q = q.filter(CupomMarketplace.ativo == ativo)
    total = q.count()
    items = q.order_by(CupomMarketplace.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": [_cupom_to_dict(c) for c in items], "total": total}


@router.post(
    "/cupons",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_superadmin())],
)
def admin_criar_cupom(
    body: dict,
    db: Session = Depends(get_db),
):
    from ...models.cupom_marketplace import CupomMarketplace
    from ...schemas.mobile import CupomAdminCreate
    parsed = CupomAdminCreate(**body)
    existente = db.query(CupomMarketplace).filter(CupomMarketplace.codigo == parsed.codigo.upper().strip()).first()
    if existente:
        raise HTTPException(409, "Código de cupom já existe")
    cupom = CupomMarketplace(
        codigo=parsed.codigo.upper().strip(),
        tipo_desconto=parsed.tipo_desconto,
        valor_desconto=parsed.valor_desconto,
        valor_minimo_pedido=parsed.valor_minimo_pedido,
        uso_maximo=parsed.uso_maximo,
        uso_maximo_por_consumidor=parsed.uso_maximo_por_consumidor,
        valido_de=parsed.valido_de,
        valido_ate=parsed.valido_ate,
        loja_id=parsed.loja_id,
    )
    db.add(cupom)
    db.commit()
    db.refresh(cupom)
    return _cupom_to_dict(cupom)


@router.patch(
    "/cupons/{cupom_id}",
    dependencies=[Depends(require_superadmin())],
)
def admin_editar_cupom(
    cupom_id: int,
    body: dict,
    db: Session = Depends(get_db),
):
    from ...models.cupom_marketplace import CupomMarketplace
    from ...schemas.mobile import CupomAdminUpdate
    parsed = CupomAdminUpdate(**body)
    cupom = db.query(CupomMarketplace).filter(CupomMarketplace.id == cupom_id).first()
    if not cupom:
        raise HTTPException(404, "Cupom não encontrado")
    for field in ("valor_desconto", "valor_minimo_pedido", "uso_maximo", "uso_maximo_por_consumidor", "valido_de", "valido_ate", "ativo"):
        val = getattr(parsed, field, None)
        if val is not None:
            setattr(cupom, field, val)
    db.commit()
    db.refresh(cupom)
    return _cupom_to_dict(cupom)


@router.delete(
    "/cupons/{cupom_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_superadmin())],
)
def admin_desativar_cupom(
    cupom_id: int,
    db: Session = Depends(get_db),
):
    from ...models.cupom_marketplace import CupomMarketplace
    cupom = db.query(CupomMarketplace).filter(CupomMarketplace.id == cupom_id).first()
    if not cupom:
        raise HTTPException(404, "Cupom não encontrado")
    cupom.ativo = False
    db.commit()


def _cupom_to_dict(c) -> dict:
    return {
        "id": c.id,
        "codigo": c.codigo,
        "tipo_desconto": c.tipo_desconto,
        "valor_desconto": float(c.valor_desconto) if c.valor_desconto else 0,
        "valor_minimo_pedido": float(c.valor_minimo_pedido) if c.valor_minimo_pedido else None,
        "uso_maximo": c.uso_maximo,
        "uso_atual": c.uso_atual,
        "uso_maximo_por_consumidor": c.uso_maximo_por_consumidor,
        "valido_de": c.valido_de.isoformat() if c.valido_de else None,
        "valido_ate": c.valido_ate.isoformat() if c.valido_ate else None,
        "ativo": c.ativo,
        "loja_id": c.loja_id,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


# ─── Admin: CRUD Motivos Cancelamento/Devolução ─────────────
@router.get(
    "/motivos-cancelamento",
    dependencies=[Depends(require_superadmin())],
)
def admin_listar_motivos(
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from ...models.motivo_cancelamento import MotivoCancelamento
    q = db.query(MotivoCancelamento)
    if tipo:
        q = q.filter(MotivoCancelamento.tipo == tipo)
    return q.order_by(MotivoCancelamento.tipo, MotivoCancelamento.ordem).all()


@router.post(
    "/motivos-cancelamento",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_superadmin())],
)
def admin_criar_motivo(
    body: dict,
    db: Session = Depends(get_db),
):
    from ...models.motivo_cancelamento import MotivoCancelamento
    from ...schemas.mobile import MotivoAdminCreate
    parsed = MotivoAdminCreate(**body)
    motivo = MotivoCancelamento(
        descricao=parsed.descricao,
        tipo=parsed.tipo,
        ordem=parsed.ordem,
    )
    db.add(motivo)
    db.commit()
    db.refresh(motivo)
    return motivo


@router.patch(
    "/motivos-cancelamento/{motivo_id}",
    dependencies=[Depends(require_superadmin())],
)
def admin_editar_motivo(
    motivo_id: int,
    body: dict,
    db: Session = Depends(get_db),
):
    from ...models.motivo_cancelamento import MotivoCancelamento
    from ...schemas.mobile import MotivoAdminUpdate
    parsed = MotivoAdminUpdate(**body)
    motivo = db.query(MotivoCancelamento).filter(MotivoCancelamento.id == motivo_id).first()
    if not motivo:
        raise HTTPException(404, "Motivo não encontrado")
    if parsed.descricao is not None:
        motivo.descricao = parsed.descricao
    if parsed.ativo is not None:
        motivo.ativo = parsed.ativo
    if parsed.ordem is not None:
        motivo.ordem = parsed.ordem
    db.commit()
    db.refresh(motivo)
    return motivo


# ─── Admin/Vendedor: Chat ────────────────────────────────────
@router.get("/loja/{loja_id}/conversas")
def admin_listar_conversas_loja(
    loja_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    db: Session = Depends(get_db),
):
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == loja_id).first()
    if not loja:
        raise HTTPException(404, "Loja não encontrada")
    if not scope.is_superadmin and loja.cliente_id not in (scope.allowed_ids or []):
        raise HTTPException(403, "Sem permissão para esta loja")
    from ...services.chat_marketplace_service import listar_conversas_loja
    items, total = listar_conversas_loja(db, loja_id, offset=offset, limit=limit)
    return {"items": items, "total": total}


@router.get("/conversas/{conversa_id}/mensagens")
def admin_listar_mensagens_conversa(
    conversa_id: int,
    before_id: int = Query(None),
    limit: int = Query(30, ge=1, le=100),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    db: Session = Depends(get_db),
):
    from ...models.conversa_marketplace import ConversaMarketplace
    from ...models.mensagem_conversa import MensagemConversa
    conversa = db.query(ConversaMarketplace).filter(ConversaMarketplace.id == conversa_id).first()
    if not conversa:
        raise HTTPException(404, "Conversa não encontrada")
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == conversa.loja_id).first()
    if not scope.is_superadmin and loja and loja.cliente_id not in (scope.allowed_ids or []):
        raise HTTPException(403, "Sem permissão")
    q = db.query(MensagemConversa).filter(MensagemConversa.conversa_id == conversa_id)
    if before_id:
        q = q.filter(MensagemConversa.id < before_id)
    return q.order_by(MensagemConversa.created_at.desc()).limit(limit).all()


@router.post("/conversas/{conversa_id}/mensagens", status_code=201)
def admin_enviar_mensagem_loja(
    conversa_id: int,
    body: dict,
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    db: Session = Depends(get_db),
):
    from ...models.conversa_marketplace import ConversaMarketplace
    conversa = db.query(ConversaMarketplace).filter(ConversaMarketplace.id == conversa_id).first()
    if not conversa:
        raise HTTPException(404, "Conversa não encontrada")
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == conversa.loja_id).first()
    if not scope.is_superadmin and loja and loja.cliente_id not in (scope.allowed_ids or []):
        raise HTTPException(403, "Sem permissão")
    from ...services.chat_marketplace_service import enviar_mensagem_loja
    try:
        msg = enviar_mensagem_loja(db, conversa_id, scope.user_id, texto=body.get("texto"), imagem_url=body.get("imagem_url"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return msg


@router.patch("/conversas/{conversa_id}/lida")
def admin_marcar_lida_loja(
    conversa_id: int,
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    db: Session = Depends(get_db),
):
    from ...services.chat_marketplace_service import marcar_lida_loja
    count = marcar_lida_loja(db, conversa_id)
    return {"marcadas": count}


# ─── Admin/Vendedor: Devoluções da loja ──────────────────────
@router.get("/loja/{loja_id}/devolucoes")
def admin_listar_devolucoes_loja(
    loja_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    db: Session = Depends(get_db),
):
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == loja_id).first()
    if not loja:
        raise HTTPException(404, "Loja não encontrada")
    if not scope.is_superadmin and loja.cliente_id not in (scope.allowed_ids or []):
        raise HTTPException(403, "Sem permissão para esta loja")
    from ...models.devolucao_marketplace import DevolucaoMarketplace
    from ...models.pedido_marketplace import PedidoMarketplace
    q = (
        db.query(DevolucaoMarketplace)
        .join(PedidoMarketplace, DevolucaoMarketplace.pedido_id == PedidoMarketplace.id)
        .filter(PedidoMarketplace.loja_id == loja_id)
    )
    if status_filter:
        q = q.filter(DevolucaoMarketplace.status == status_filter)
    total = q.count()
    items = q.order_by(DevolucaoMarketplace.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": items, "total": total}


@router.patch("/devolucoes/{devolucao_id}")
def admin_responder_devolucao(
    devolucao_id: int,
    body: dict,
    scope: ClienteScope = Depends(get_cliente_scope_dep),
    db: Session = Depends(get_db),
):
    from ...schemas.mobile import DevolucaoAdminUpdate
    from ...services.devolucao_service import responder_devolucao
    parsed = DevolucaoAdminUpdate(**body)
    try:
        dev = responder_devolucao(
            db,
            devolucao_id=devolucao_id,
            respondido_por=scope.user_id,
            status=parsed.status,
            resposta=parsed.resposta,
            valor_reembolso=parsed.valor_reembolso,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return dev


@router.post(
    "/admin/reparar-comprador-pedidos",
    response_model=ReparacaoCompradorResultado,
)
def reparar_comprador_pedidos_endpoint(
    payload: ReparacaoCompradorRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    """Super Admin: reatribui `comprador_id` de pedidos antigos cujo dono e um guest duplicado.

    Match por (tenant_id, email_normalizado) entre consumidor REGISTERED e guests.
    Pedidos cujo `comprador_id` aponta para guest duplicado sao reatribuidos para o registered.
    `dry_run=True` (default) so relata; `dry_run=False` aplica e grava `audit_log` + eventos
    de timeline (`tipo_evento=reatribuicao_comprador`, `actor_type=super_admin`).
    """
    try:
        resultado = reparar_comprador_pedidos(
            db,
            tenant_id=payload.tenant_id,
            email=payload.email,
            dry_run=payload.dry_run,
            actor_user_id=current_user.id,
            request_ip=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not payload.dry_run:
        db.commit()
    return resultado
