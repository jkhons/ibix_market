# PDV Ibix - API Produtos por Estabelecimento (Fase 2 - Plano Hierarquia)
"""CRUD de produtos_cliente e códigos de barras. Escopo por cliente_id."""
import base64
import ipaddress
import json
import os
import re
import socket
import uuid
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, get_current_user
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models import Cliente, CodigoBarrasCliente, ProdutoCliente, Usuario
from ...schemas.produto_cliente import ProdutoClienteCreate, ProdutoClienteResponse, ProdutoClienteUpdate

router = APIRouter(prefix="/produtos-cliente", tags=["Produtos (estabelecimento)"])

# Diretório para fotos e mídias de produtos (servido em /static/uploads/produtos/)
UPLOAD_PRODUTOS_DIR = "app/static/uploads/produtos"
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
MIME_IMAGE_TO_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}
MIME_VIDEO_TO_EXT = {"video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov"}
# Limite vídeo: 80 MB (comprima antes de enviar)
MAX_VIDEO_BYTES = 80 * 1024 * 1024
# Limite por imagem (evitar arquivos gigantes; padrão marketplaces ~5MB)
MAX_IMAGE_BYTES = 5 * 1024 * 1024
# Limite imagens por produto (além da foto_peca) — alinhado a ML/Amazon
MAX_IMAGENS_MIDIAS = 12
MAX_VIDEOS_MIDIAS = 2


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


def _save_foto_base64(blob_b64: str, cliente_id: int, produto_id: int) -> str:
    """Decodifica imagem em base64 (data URL ou puro), salva em disco. Retorna path relativo: uploads/produtos/..."""
    if not blob_b64 or not blob_b64.strip():
        raise ValueError("Imagem vazia")
    raw = blob_b64.strip()
    m = re.match(r"^data:([^;]+);base64,(.+)$", raw, re.DOTALL)
    if m:
        mime = m.group(1).strip().lower()
        b64 = m.group(2)
        ext = MIME_IMAGE_TO_EXT.get(mime, ".jpg")
    else:
        b64 = raw
        ext = ".jpg"
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = ".jpg"
    try:
        content = base64.b64decode(b64)
    except Exception as e:
        raise ValueError(f"Base64 inválido: {e}")
    if not content:
        raise ValueError("Conteúdo da imagem vazio")
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError(f"Imagem excede o limite de {MAX_IMAGE_BYTES // (1024*1024)} MB. Reduza o tamanho ou resolução.")
    subdir = os.path.join(str(cliente_id), str(produto_id))
    save_dir = os.path.join(UPLOAD_PRODUTOS_DIR, subdir)
    os.makedirs(save_dir, exist_ok=True)
    filename = f"foto_{uuid.uuid4().hex[:12]}{ext}"
    file_path = os.path.join(save_dir, filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return f"uploads/produtos/{subdir}/{filename}"


def _append_midias_list(produto: ProdutoCliente, new_items: list) -> None:
    """Append new midias to produto.midias (JSON string in DB). new_items = [{"tipo": "imagem"|"video", "url": str}]."""
    current = []
    if produto.midias:
        try:
            current = json.loads(produto.midias) if isinstance(produto.midias, str) else list(produto.midias)
        except (TypeError, json.JSONDecodeError):
            current = []
    if not isinstance(current, list):
        current = []
    current.extend(new_items)
    produto.midias = json.dumps(current) if current else None


def _allowed_cliente_ids(scope: ClienteScope) -> Optional[List[int]]:
    if not scope.must_filter_by_cliente():
        return None
    return scope.allowed_ids or []


def _gtin_valido(val: Optional[str]) -> Optional[str]:
    """Retorna o GTIN limpo (só dígitos) se for 8, 12, 13 ou 14 dígitos; senão None."""
    if not val or not isinstance(val, str):
        return None
    limpo = "".join(c for c in val.strip() if c.isdigit())
    return limpo if len(limpo) in (8, 12, 13, 14) else None


def _get_principal_codigo_barras(db: Session, produto_id: int) -> Optional[str]:
    cb = (
        db.query(CodigoBarrasCliente)
        .filter(
            CodigoBarrasCliente.produto_cliente_id == produto_id,
            CodigoBarrasCliente.principal == True,
        )
        .first()
    )
    return cb.codigo_barras if cb else None


def _produto_response(db: Session, p: ProdutoCliente, cliente_nome: Optional[str] = None) -> ProdutoClienteResponse:
    data = ProdutoClienteResponse.model_validate(p).model_dump()
    data["codigo_barras"] = _get_principal_codigo_barras(db, p.id)
    if cliente_nome is not None:
        data["cliente_nome"] = cliente_nome
    return ProdutoClienteResponse(**data)


@router.get("/", response_model=dict)
async def listar_produtos(
    cliente_id: Optional[int] = Query(None, description="Filtrar por estabelecimento (obrigatório para Admin/CA)"),
    busca: Optional[str] = Query(None),
    ativo: Optional[bool] = None,
    categoria_id: Optional[int] = Query(None, description="Filtrar por categoria de material"),
    tipo_material_id: Optional[int] = Query(None, description="Filtrar por tipo de material"),
    sem_imagem: Optional[bool] = Query(None, description="Filtrar produtos sem imagem (foto_peca nem mídia imagem)"),
    sem_tipo: Optional[bool] = Query(None, description="Filtrar produtos sem tipo de material"),
    sem_categoria: Optional[bool] = Query(None, description="Filtrar produtos sem categoria"),
    sem_preco_venda: Optional[bool] = Query(None, description="Filtrar produtos sem preço de venda"),
    sem_descricao: Optional[bool] = Query(None, description="Filtrar produtos sem descrição (nula ou só espaços)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista produtos do estabelecimento com paginação. Retorna {items, total, skip, limit}."""
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and not allowed:
        return {"items": [], "total": 0, "skip": skip, "limit": limit}
    q = db.query(ProdutoCliente)
    if allowed is not None:
        q = q.filter(ProdutoCliente.cliente_id.in_(allowed))
    if cliente_id is not None:
        if allowed is not None and cliente_id not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Estabelecimento fora do escopo")
        q = q.filter(ProdutoCliente.cliente_id == cliente_id)
    if busca:
        q = q.filter(
            ProdutoCliente.codigo.ilike(f"%{busca}%") | ProdutoCliente.nome.ilike(f"%{busca}%")
        )
    if ativo is not None:
        q = q.filter(ProdutoCliente.ativo == ativo)
    if categoria_id is not None:
        q = q.filter(ProdutoCliente.categoria_id == categoria_id)
    if tipo_material_id is not None:
        q = q.filter(ProdutoCliente.tipo_material_id == tipo_material_id)
    if sem_tipo is True:
        q = q.filter(ProdutoCliente.tipo_material_id == None)
    if sem_categoria is True:
        q = q.filter(ProdutoCliente.categoria_id == None)
    if sem_preco_venda is True:
        q = q.filter((ProdutoCliente.valor_venda == None) | (ProdutoCliente.valor_venda <= 0))
    if sem_descricao is True:
        q = q.filter(
            or_(
                ProdutoCliente.descricao.is_(None),
                func.length(func.coalesce(func.trim(ProdutoCliente.descricao), "")) == 0,
            )
        )
    if sem_imagem is True:
        all_rows = q.order_by(ProdutoCliente.codigo).all()
        filtered = []
        for r in all_rows:
            has_foto = bool(r.foto_peca and str(r.foto_peca).strip())
            has_imagem_midias = False
            if not has_foto and r.midias:
                try:
                    midias = json.loads(r.midias) if isinstance(r.midias, str) else (r.midias or [])
                    if isinstance(midias, list):
                        for m in midias:
                            if isinstance(m, dict) and (m.get("tipo") or "").lower() == "imagem":
                                has_imagem_midias = True
                                break
                except (TypeError, json.JSONDecodeError):
                    pass
            if not has_foto and not has_imagem_midias:
                filtered.append(r)
        total = len(filtered)
        rows = filtered[skip : skip + limit]
    else:
        total = q.count()
        rows = q.order_by(ProdutoCliente.codigo).offset(skip).limit(limit).all()
    if rows:
        ids = [r.id for r in rows]
        cbs = (
            db.query(CodigoBarrasCliente)
            .filter(
                CodigoBarrasCliente.produto_cliente_id.in_(ids),
                CodigoBarrasCliente.principal == True,
            )
            .all()
        )
        map_cb = {cb.produto_cliente_id: cb.codigo_barras for cb in cbs}
        cliente_ids_uniq = list({r.cliente_id for r in rows})
        map_cliente_nome = {}
        if cliente_ids_uniq:
            clientes = db.query(Cliente.id, Cliente.nome).filter(Cliente.id.in_(cliente_ids_uniq)).all()
            map_cliente_nome = {c.id: (c.nome or "").strip() for c in clientes}
        items = []
        for r in rows:
            data = ProdutoClienteResponse.model_validate(r).model_dump()
            data["codigo_barras"] = map_cb.get(r.id)
            data["cliente_nome"] = map_cliente_nome.get(r.cliente_id)
            items.append(ProdutoClienteResponse(**data))
    else:
        items = []
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/stats", response_model=dict)
async def stats_produtos(
    cliente_id: int = Query(..., description="Estabelecimento (obrigatório)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Retorna contagens de pendências de produto. Escopo por tenant."""
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and cliente_id not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Estabelecimento fora do escopo")
    q = db.query(ProdutoCliente).filter(ProdutoCliente.cliente_id == cliente_id)
    rows = q.all()
    sem_imagem = 0
    sem_tipo = 0
    sem_categoria = 0
    sem_preco_venda = 0
    sem_descricao = 0
    for p in rows:
        if p.tipo_material_id is None:
            sem_tipo += 1
        if p.categoria_id is None:
            sem_categoria += 1
        if p.valor_venda is None or p.valor_venda <= 0:
            sem_preco_venda += 1
        if not (p.descricao or "").strip():
            sem_descricao += 1
        has_foto = bool(p.foto_peca and str(p.foto_peca).strip())
        has_imagem_midias = False
        if not has_foto and p.midias:
            try:
                midias = json.loads(p.midias) if isinstance(p.midias, str) else (p.midias or [])
                if isinstance(midias, list):
                    for m in midias:
                        if isinstance(m, dict) and (m.get("tipo") or "").lower() == "imagem":
                            has_imagem_midias = True
                            break
            except (TypeError, json.JSONDecodeError):
                pass
        if not has_foto and not has_imagem_midias:
            sem_imagem += 1
    return {
        "sem_imagem": sem_imagem,
        "sem_tipo": sem_tipo,
        "sem_categoria": sem_categoria,
        "sem_preco_venda": sem_preco_venda,
        "sem_descricao": sem_descricao,
    }


@router.get("/por-codigo-barras", response_model=Optional[ProdutoClienteResponse])
async def obter_produto_por_codigo_barras(
    codigo_barras: str = Query(..., min_length=1),
    cliente_id: int = Query(..., description="Estabelecimento para buscar"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Retorna produto do estabelecimento que possui o código de barras (para leitura no PDV)."""
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Estabelecimento fora do escopo")
    cb = db.query(CodigoBarrasCliente).filter(CodigoBarrasCliente.codigo_barras == codigo_barras).first()
    if not cb:
        return None
    p = db.query(ProdutoCliente).filter(ProdutoCliente.id == cb.produto_cliente_id).first()
    if not p or p.cliente_id != cliente_id:
        return None
    if allowed is not None and p.cliente_id not in allowed:
        return None
    return _produto_response(db, p)


@router.get("/{produto_id}", response_model=ProdutoClienteResponse)
async def obter_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Obtém produto por ID. Estabelecimento do produto deve estar no escopo."""
    p = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and p.cliente_id not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Produto fora do escopo")
    return _produto_response(db, p)


@router.post("/", response_model=ProdutoClienteResponse, status_code=status.HTTP_201_CREATED)
async def criar_produto(
    body: ProdutoClienteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Cria produto no estabelecimento. cliente_id deve estar no escopo."""
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and body.cliente_id not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Estabelecimento fora do escopo")
    existing = db.query(ProdutoCliente).filter(
        ProdutoCliente.cliente_id == body.cliente_id,
        ProdutoCliente.codigo == body.codigo,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe produto com este código neste estabelecimento",
        )
    qtd = body.quantidade_atual if body.quantidade_atual is not None else 0
    p = ProdutoCliente(
        cliente_id=body.cliente_id,
        codigo=body.codigo,
        nome=body.nome,
        descricao=body.descricao,
        ncm=body.ncm,
        cfop_padrao=body.cfop_padrao,
        cest=getattr(body, "cest", None),
        extipi=getattr(body, "extipi", None),
        origem_mercadoria=getattr(body, "origem_mercadoria", None),
        referencia=body.referencia,
        unidade_medida=body.unidade_medida,
        valor_custo=body.valor_custo,
        valor_venda=body.valor_venda,
        quantidade_atual=qtd,
        quantidade_minima=body.quantidade_minima,
        ativo=body.ativo,
        categoria_id=getattr(body, "categoria_id", None),
        tipo_material_id=getattr(body, "tipo_material_id", None),
        categoria=getattr(body, "categoria", None),
        tipo_material=getattr(body, "tipo_material", None),
        fabricante=getattr(body, "fabricante", None),
        fornecedor=getattr(body, "fornecedor", None),
        data_validade=getattr(body, "data_validade", None),
        data_fabricacao=getattr(body, "data_fabricacao", None),
        controla_estoque=getattr(body, "controla_estoque", True),
        quantidade_maxima=getattr(body, "quantidade_maxima", None),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    foto_peca_base64 = getattr(body, "foto_peca_base64", None)
    if foto_peca_base64:
        try:
            p.foto_peca = _save_foto_base64(foto_peca_base64, p.cliente_id, p.id)
            db.commit()
            db.refresh(p)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Imagem principal inválida: " + str(e),
            )
    codigo_barras = getattr(body, "codigo_barras", None)
    gtin = _gtin_valido(codigo_barras)
    if gtin:
        existing_cb = db.query(CodigoBarrasCliente).filter(CodigoBarrasCliente.codigo_barras == gtin).first()
        if existing_cb:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este código de barras (GTIN) já está em uso em outro produto",
            )
        cb = CodigoBarrasCliente(produto_cliente_id=p.id, codigo_barras=gtin, principal=True)
        db.add(cb)
        db.commit()
    return _produto_response(db, p)


@router.patch("/{produto_id}", response_model=ProdutoClienteResponse)
async def atualizar_produto(
    produto_id: int,
    body: ProdutoClienteUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Atualiza produto. Estabelecimento do produto deve estar no escopo."""
    p = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and p.cliente_id not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Produto fora do escopo")
    data = body.model_dump(exclude_unset=True, exclude={"foto_peca_base64", "codigo_barras"})
    if "codigo" in data:
        other = db.query(ProdutoCliente).filter(
            ProdutoCliente.cliente_id == p.cliente_id,
            ProdutoCliente.codigo == data["codigo"],
            ProdutoCliente.id != produto_id,
        ).first()
        if other:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe outro produto com este código neste estabelecimento",
            )
    for k, v in data.items():
        if k == "midias" and v is not None and isinstance(v, list):
            setattr(p, k, json.dumps(v))
        else:
            setattr(p, k, v)
    foto_peca_base64 = getattr(body, "foto_peca_base64", None)
    if foto_peca_base64:
        try:
            p.foto_peca = _save_foto_base64(foto_peca_base64, p.cliente_id, p.id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Imagem principal inválida: " + str(e),
            )
    db.commit()
    db.refresh(p)
    if "codigo_barras" in body.model_dump(exclude_unset=True):
        gtin = _gtin_valido(getattr(body, "codigo_barras", None))
        principal_cb = (
            db.query(CodigoBarrasCliente)
            .filter(
                CodigoBarrasCliente.produto_cliente_id == produto_id,
                CodigoBarrasCliente.principal == True,
            )
            .first()
        )
        if gtin:
            if not principal_cb or principal_cb.codigo_barras != gtin:
                existing = db.query(CodigoBarrasCliente).filter(CodigoBarrasCliente.codigo_barras == gtin).first()
                if existing and existing.produto_cliente_id != produto_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Este código de barras (GTIN) já está em uso em outro produto",
                    )
                if principal_cb:
                    db.delete(principal_cb)
                db.add(CodigoBarrasCliente(produto_cliente_id=produto_id, codigo_barras=gtin, principal=True))
        else:
            if principal_cb:
                db.delete(principal_cb)
        db.commit()
    db.refresh(p)
    return _produto_response(db, p)


@router.delete("/{produto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Exclui produto. Estabelecimento do produto deve estar no escopo."""
    p = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and p.cliente_id not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Produto fora do escopo")
    db.delete(p)
    db.commit()
    return None


class CodigoBarrasCreate(BaseModel):
    codigo_barras: str
    principal: bool = False


class CodigoBarrasResponse(BaseModel):
    id: int
    produto_cliente_id: int
    codigo_barras: str
    principal: bool


@router.get("/{produto_id}/codigos-barras", response_model=List[CodigoBarrasResponse])
async def listar_codigos_barras(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista códigos de barras do produto."""
    p = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if _allowed_cliente_ids(scope) is not None and p.cliente_id not in (_allowed_cliente_ids(scope) or []):
        raise HTTPException(status_code=403, detail="Produto fora do escopo")
    rows = db.query(CodigoBarrasCliente).filter(CodigoBarrasCliente.produto_cliente_id == produto_id).all()
    return [CodigoBarrasResponse.model_validate(r) for r in rows]


@router.post("/{produto_id}/codigos-barras", response_model=CodigoBarrasResponse, status_code=status.HTTP_201_CREATED)
async def adicionar_codigo_barras(
    produto_id: int,
    body: CodigoBarrasCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Adiciona código de barras ao produto. codigo_barras é único globalmente."""
    p = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if _allowed_cliente_ids(scope) is not None and p.cliente_id not in (_allowed_cliente_ids(scope) or []):
        raise HTTPException(status_code=403, detail="Produto fora do escopo")
    existing = db.query(CodigoBarrasCliente).filter(CodigoBarrasCliente.codigo_barras == body.codigo_barras).first()
    if existing:
        raise HTTPException(status_code=409, detail="Este código de barras já está em uso")
    cb = CodigoBarrasCliente(produto_cliente_id=produto_id, codigo_barras=body.codigo_barras.strip(), principal=body.principal)
    db.add(cb)
    db.commit()
    db.refresh(cb)
    return CodigoBarrasResponse.model_validate(cb)


@router.delete("/{produto_id}/codigos-barras/{codigo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_codigo_barras(
    produto_id: int,
    codigo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Remove código de barras do produto."""
    p = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if _allowed_cliente_ids(scope) is not None and p.cliente_id not in (_allowed_cliente_ids(scope) or []):
        raise HTTPException(status_code=403, detail="Produto fora do escopo")
    cb = db.query(CodigoBarrasCliente).filter(
        CodigoBarrasCliente.id == codigo_id,
        CodigoBarrasCliente.produto_cliente_id == produto_id,
    ).first()
    if not cb:
        raise HTTPException(status_code=404, detail="Código de barras não encontrado")
    db.delete(cb)
    db.commit()
    return None


@router.post("/{produto_id}/midias", response_model=ProdutoClienteResponse)
async def upload_midias_produto(
    produto_id: int,
    files: List[UploadFile] = File(..., description="Imagens ou vídeos (máx 10 imagens, 2 vídeos; vídeo até 80MB)"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Envia múltiplas imagens ou vídeos para o produto. Limites: 10 imagens, 2 vídeos; vídeo máx 80MB."""
    p = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if _allowed_cliente_ids(scope) is not None and p.cliente_id not in (_allowed_cliente_ids(scope) or []):
        raise HTTPException(status_code=403, detail="Produto fora do escopo")
    current_midias = []
    if p.midias:
        try:
            current_midias = json.loads(p.midias) if isinstance(p.midias, str) else list(p.midias)
        except (TypeError, json.JSONDecodeError):
            pass
    n_imagens = sum(1 for m in current_midias if m.get("tipo") == "imagem")
    n_videos = sum(1 for m in current_midias if m.get("tipo") == "video")
    added = []
    subdir = os.path.join(str(p.cliente_id), str(p.id))
    save_dir = os.path.join(UPLOAD_PRODUTOS_DIR, subdir)
    os.makedirs(save_dir, exist_ok=True)
    for f in files:
        if not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        content_type = (f.content_type or "").lower()
        if ext in ALLOWED_IMAGE_EXTENSIONS or content_type in MIME_IMAGE_TO_EXT:
            if n_imagens >= MAX_IMAGENS_MIDIAS:
                raise HTTPException(status_code=400, detail=f"Máximo de {MAX_IMAGENS_MIDIAS} imagens por produto")
            content = await f.read()
            if len(content) > MAX_IMAGE_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cada imagem deve ter no máximo {MAX_IMAGE_BYTES // (1024*1024)} MB. Reduza o tamanho ou resolução.",
                )
            ext = ext if ext in ALLOWED_IMAGE_EXTENSIONS else MIME_IMAGE_TO_EXT.get(content_type, ".jpg")
            filename = f"img_{uuid.uuid4().hex[:12]}{ext}"
            file_path = os.path.join(save_dir, filename)
            with open(file_path, "wb") as out:
                out.write(content)
            rel = f"uploads/produtos/{subdir}/{filename}"
            added.append({"tipo": "imagem", "url": rel})
            n_imagens += 1
        elif ext in ALLOWED_VIDEO_EXTENSIONS or content_type in MIME_VIDEO_TO_EXT:
            if n_videos >= MAX_VIDEOS_MIDIAS:
                raise HTTPException(status_code=400, detail=f"Máximo de {MAX_VIDEOS_MIDIAS} vídeos por produto")
            content = await f.read()
            if len(content) > MAX_VIDEO_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Vídeo excede o limite de {MAX_VIDEO_BYTES // (1024*1024)} MB. Comprima o vídeo antes de enviar.",
                )
            ext = ext if ext in ALLOWED_VIDEO_EXTENSIONS else MIME_VIDEO_TO_EXT.get(content_type, ".mp4")
            filename = f"vid_{uuid.uuid4().hex[:12]}{ext}"
            file_path = os.path.join(save_dir, filename)
            with open(file_path, "wb") as out:
                out.write(content)
            rel = f"uploads/produtos/{subdir}/{filename}"
            added.append({"tipo": "video", "url": rel})
            n_videos += 1
    if added:
        current_midias.extend(added)
        p.midias = json.dumps(current_midias)
        db.commit()
        db.refresh(p)
    return ProdutoClienteResponse.model_validate(p)


class MidiaImportUrlBody(BaseModel):
    url: str


@router.post("/{produto_id}/midias/import-url", response_model=ProdutoClienteResponse)
async def importar_midia_por_url(
    produto_id: int,
    body: MidiaImportUrlBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Baixa uma imagem externa e salva em uploads/produtos para não depender de host de terceiros."""
    p = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if _allowed_cliente_ids(scope) is not None and p.cliente_id not in (_allowed_cliente_ids(scope) or []):
        raise HTTPException(status_code=403, detail="Produto fora do escopo")

    url_str = (body.url or "").strip()
    if not url_str:
        raise HTTPException(status_code=400, detail="URL da imagem é obrigatória")
    if not _host_is_safe(url_str):
        raise HTTPException(status_code=400, detail="URL inválida ou não permitida para download")

    current_midias = _midias_list(p)
    n_imagens = sum(1 for m in current_midias if isinstance(m, dict) and m.get("tipo") == "imagem")
    if n_imagens >= MAX_IMAGENS_MIDIAS:
        raise HTTPException(status_code=400, detail=f"Máximo de {MAX_IMAGENS_MIDIAS} imagens por produto")

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url_str, headers={"User-Agent": "PDV-Ibix/1.0 (produto-imagem-import-url)"})
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Falha ao baixar imagem: {e}") from e

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Download retornou HTTP {resp.status_code}")

    ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    if not ctype.startswith("image/"):
        raise HTTPException(status_code=400, detail="URL não retornou uma imagem válida")

    content = resp.content
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Cada imagem deve ter no máximo {MAX_IMAGE_BYTES // (1024*1024)} MB. Reduza o tamanho ou resolução.",
        )

    ext = MIME_IMAGE_TO_EXT.get(ctype, ".jpg")
    subdir = os.path.join(str(p.cliente_id), str(p.id))
    save_dir = os.path.join(UPLOAD_PRODUTOS_DIR, subdir)
    os.makedirs(save_dir, exist_ok=True)
    filename = f"img_{uuid.uuid4().hex[:12]}{ext}"
    file_path = os.path.join(save_dir, filename)
    with open(file_path, "wb") as out:
        out.write(content)

    rel = f"uploads/produtos/{subdir}/{filename}"
    current_midias.append({"tipo": "imagem", "url": rel})
    p.midias = json.dumps(current_midias)
    db.commit()
    db.refresh(p)
    return ProdutoClienteResponse.model_validate(p)


def _midias_list(produto: ProdutoCliente) -> list:
    """Retorna lista de mídias do produto (dicts com tipo, url)."""
    if not produto.midias:
        return []
    try:
        out = json.loads(produto.midias) if isinstance(produto.midias, str) else list(produto.midias)
        return out if isinstance(out, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


@router.delete("/{produto_id}/midias/{index}", response_model=ProdutoClienteResponse)
async def remover_midia_produto(
    produto_id: int,
    index: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Remove uma mídia da lista pelo índice (0-based). Opcionalmente remove o arquivo do disco."""
    if index < 0:
        raise HTTPException(status_code=400, detail="Índice inválido")
    p = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if _allowed_cliente_ids(scope) is not None and p.cliente_id not in (_allowed_cliente_ids(scope) or []):
        raise HTTPException(status_code=403, detail="Produto fora do escopo")
    current = _midias_list(p)
    if index >= len(current):
        raise HTTPException(status_code=404, detail="Mídia não encontrada neste índice")
    removed = current.pop(index)
    url = removed.get("url") if isinstance(removed, dict) else None
    if url and isinstance(url, str) and url.startswith("uploads/produtos/"):
        file_path = os.path.join("app/static", url)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
    p.midias = json.dumps(current) if current else None
    db.commit()
    db.refresh(p)
    return ProdutoClienteResponse.model_validate(p)


class MidiasOrdemBody(BaseModel):
    """Lista ordenada de mídias (mesma estrutura: tipo, url)."""

    midias: List[dict]


@router.patch("/{produto_id}/midias/ordem", response_model=ProdutoClienteResponse)
async def reordenar_midias_produto(
    produto_id: int,
    body: MidiasOrdemBody,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Define a nova ordem das mídias (primeira = destaque na listagem/vitrine)."""
    p = db.query(ProdutoCliente).filter(ProdutoCliente.id == produto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if _allowed_cliente_ids(scope) is not None and p.cliente_id not in (_allowed_cliente_ids(scope) or []):
        raise HTTPException(status_code=403, detail="Produto fora do escopo")
    _midias_list(p)
    if not body.midias:
        p.midias = None
    else:
        valid = [m for m in body.midias if isinstance(m, dict) and m.get("url")]
        p.midias = json.dumps(valid)
    db.commit()
    db.refresh(p)
    return ProdutoClienteResponse.model_validate(p)
