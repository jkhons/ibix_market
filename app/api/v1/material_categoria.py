# PDV Ibix - API Categorias de Material (estoque)
"""CRUD de material_categoria para classificação de produtos no estoque."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.middleware import forbid_cliente_access, get_current_user, require_superadmin
from ...database.connection import get_db
from ...models import MaterialCategoria, Usuario
from ...schemas.material_categoria import (
    MaterialCategoriaCreate,
    MaterialCategoriaResponse,
    MaterialCategoriaUpdate,
)

router = APIRouter(prefix="/material-categorias", tags=["Estoque - Categorias de material"])


@router.get("/", response_model=List[MaterialCategoriaResponse])
async def listar_material_categorias(
    ativo: Optional[bool] = Query(None, description="Filtrar por ativo (True/False); omitir = todos"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Lista categorias de material para uso em produtos (estoque)."""
    q = db.query(MaterialCategoria)
    if ativo is not None:
        q = q.filter(MaterialCategoria.ativo == ativo)
    rows = q.order_by(MaterialCategoria.nome).offset(skip).limit(limit).all()
    return [MaterialCategoriaResponse.model_validate(r) for r in rows]


@router.get("/{categoria_id}", response_model=MaterialCategoriaResponse)
async def obter_material_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Obtém uma categoria de material por ID."""
    cat = db.query(MaterialCategoria).filter(MaterialCategoria.id == categoria_id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")
    return MaterialCategoriaResponse.model_validate(cat)


@router.post("/", response_model=MaterialCategoriaResponse, status_code=status.HTTP_201_CREATED)
async def criar_material_categoria(
    body: MaterialCategoriaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    __: None = Depends(require_superadmin()),
):
    """Cria categoria de material. Apenas Superadministrador."""
    codigo = body.codigo.strip().upper()
    nome = body.nome.strip()
    if db.query(MaterialCategoria).filter(MaterialCategoria.codigo == codigo).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe categoria com este código")
    if db.query(MaterialCategoria).filter(MaterialCategoria.nome == nome).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe categoria com este nome")
    cat = MaterialCategoria(
        codigo=codigo,
        nome=nome,
        descricao=body.descricao,
        icone=(body.icone.strip() if body.icone else None),
        ativo=body.ativo,
        controla_estoque=body.controla_estoque,
        permite_negativo=body.permite_negativo,
        tem_validade=body.tem_validade,
        dias_alerta_vencimento=body.dias_alerta_vencimento,
        requer_aprovacao=body.requer_aprovacao,
        limite_movimentacao=body.limite_movimentacao,
        incluir_relatorios=body.incluir_relatorios,
        cor_relatorio=body.cor_relatorio or "#007bff",
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return MaterialCategoriaResponse.model_validate(cat)


@router.patch("/{categoria_id}", response_model=MaterialCategoriaResponse)
async def atualizar_material_categoria(
    categoria_id: int,
    body: MaterialCategoriaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
    __: None = Depends(require_superadmin()),
):
    """Atualiza categoria de material. Apenas Superadministrador."""
    cat = db.query(MaterialCategoria).filter(MaterialCategoria.id == categoria_id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")
    payload = body.model_dump(exclude_unset=True)
    if "codigo" in payload and payload["codigo"] is not None:
        payload["codigo"] = payload["codigo"].strip().upper()
        outro = db.query(MaterialCategoria).filter(MaterialCategoria.codigo == payload["codigo"], MaterialCategoria.id != categoria_id).first()
        if outro:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe categoria com este código")
    if "nome" in payload and payload["nome"] is not None:
        payload["nome"] = payload["nome"].strip()
        outro = db.query(MaterialCategoria).filter(MaterialCategoria.nome == payload["nome"], MaterialCategoria.id != categoria_id).first()
        if outro:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe categoria com este nome")
    if "icone" in payload and payload["icone"] is not None:
        payload["icone"] = payload["icone"].strip() or None
    for k, v in payload.items():
        setattr(cat, k, v)
    db.commit()
    db.refresh(cat)
    return MaterialCategoriaResponse.model_validate(cat)
