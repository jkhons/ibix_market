# PDV Ibix - API Tipos de Material (estoque)
"""CRUD de tipo_material para classificação de produtos no estoque."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.middleware import forbid_cliente_access, get_current_user
from ...database.connection import get_db
from ...models import TipoMaterial, Usuario
from ...schemas.tipo_material import TipoMaterialCreate, TipoMaterialResponse, TipoMaterialUpdate

router = APIRouter(prefix="/tipo-material", tags=["Estoque - Tipos de material"])


@router.get("/", response_model=List[TipoMaterialResponse])
async def listar_tipos_material(
    ativo: Optional[bool] = Query(None, description="Filtrar por ativo (True/False); omitir = todos"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Lista tipos de material para uso em produtos (estoque)."""
    q = db.query(TipoMaterial)
    if ativo is not None:
        q = q.filter(TipoMaterial.ativo == ativo)
    rows = q.order_by(TipoMaterial.nome).offset(skip).limit(limit).all()
    return [TipoMaterialResponse.model_validate(r) for r in rows]


@router.get("/{tipo_id}", response_model=TipoMaterialResponse)
async def obter_tipo_material(
    tipo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Obtém um tipo de material por ID."""
    t = db.query(TipoMaterial).filter(TipoMaterial.id == tipo_id).first()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de material não encontrado")
    return TipoMaterialResponse.model_validate(t)


@router.post("/", response_model=TipoMaterialResponse, status_code=status.HTTP_201_CREATED)
async def criar_tipo_material(
    body: TipoMaterialCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Cria tipo de material."""
    codigo = body.codigo.strip().upper()
    nome = body.nome.strip()
    if db.query(TipoMaterial).filter(TipoMaterial.codigo == codigo).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe tipo com este código")
    t = TipoMaterial(codigo=codigo, nome=nome, ativo=body.ativo)
    db.add(t)
    db.commit()
    db.refresh(t)
    return TipoMaterialResponse.model_validate(t)


@router.patch("/{tipo_id}", response_model=TipoMaterialResponse)
async def atualizar_tipo_material(
    tipo_id: int,
    body: TipoMaterialUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(forbid_cliente_access),
):
    """Atualiza tipo de material."""
    t = db.query(TipoMaterial).filter(TipoMaterial.id == tipo_id).first()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de material não encontrado")
    payload = body.model_dump(exclude_unset=True)
    if "codigo" in payload and payload["codigo"] is not None:
        payload["codigo"] = payload["codigo"].strip().upper()
        outro = db.query(TipoMaterial).filter(TipoMaterial.codigo == payload["codigo"], TipoMaterial.id != tipo_id).first()
        if outro:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe tipo com este código")
    if "nome" in payload and payload["nome"] is not None:
        payload["nome"] = payload["nome"].strip()
    for k, v in payload.items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return TipoMaterialResponse.model_validate(t)
