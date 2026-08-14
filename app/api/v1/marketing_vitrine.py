# PDV Ibix — Marketing Vitrine (config global + cards; Superadmin; GET público)
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ...core.middleware import require_superadmin
from ...database.connection import get_db
from ...models import Cliente, LojaMarketplace, MarketingVitrineCard, Usuario
from ...schemas.marketing_vitrine import (
    MarketingVitrineCardAdminResponse,
    MarketingVitrineCardCreate,
    MarketingVitrineCardUpdate,
    MarketingVitrineConfigResponse,
    MarketingVitrineConfigUpdate,
)
from ...services.marketing_vitrine_service import (
    build_public_payload,
    get_or_create_config_row,
    listar_anuncios_picklist_vitrine,
    validar_anuncio_vinculo,
)

from ...core.brand_module_gating import MARKETPLACE_ROUTER_DEPENDENCIES

router = APIRouter(
    prefix="/marketing-vitrine",
    tags=["Marketing Vitrine"],
    dependencies=MARKETPLACE_ROUTER_DEPENDENCIES,
)


def _merge_card_create_from_row(row: MarketingVitrineCard, body: MarketingVitrineCardUpdate) -> MarketingVitrineCardCreate:
    patch = body.model_dump(exclude_unset=True)
    tipo_bloco = body.tipo_bloco if body.tipo_bloco is not None else row.tipo_bloco
    tipo_card = body.tipo_card if body.tipo_card is not None else row.tipo_card

    def pk(key: str, default=None):
        if key in patch:
            return patch[key]
        return getattr(row, key, default)

    if tipo_card == "anuncio":
        aids = body.anuncio_ids if body.anuncio_ids is not None else getattr(row, "anuncio_ids", None)
        emb = None
        if tipo_bloco in ("oferta_semana", "destaque_agora"):
            if "embaralhar_produtos" in patch:
                emb = bool(body.embaralhar_produtos) if body.embaralhar_produtos is not None else False
            else:
                ev = getattr(row, "embaralhar_produtos", None)
                emb = bool(ev) if ev is not None else False
        return MarketingVitrineCardCreate(
            tipo_bloco=tipo_bloco,  # type: ignore[arg-type]
            tipo_card=tipo_card,  # type: ignore[arg-type]
            titulo=None,
            descricao=body.descricao if body.descricao is not None else row.descricao,
            imagem_url=None,
            link_url=None,
            anuncio_id=body.anuncio_id if body.anuncio_id is not None else row.anuncio_id,
            anuncio_ids=aids,
            limite_exibicao=None,
            cliente_ids=None,
            embaralhar_produtos=emb,
            somente_com_desconto=None,
            ordem=body.ordem if body.ordem is not None else row.ordem,
            ativo=body.ativo if body.ativo is not None else row.ativo,
            inicio_em=body.inicio_em if body.inicio_em is not None else row.inicio_em,
            fim_em=body.fim_em if body.fim_em is not None else row.fim_em,
        )
    if tipo_card == "cabecalho_ofertas":
        return MarketingVitrineCardCreate(
            tipo_bloco=tipo_bloco,  # type: ignore[arg-type]
            tipo_card=tipo_card,  # type: ignore[arg-type]
            titulo=pk("titulo"),
            descricao=pk("descricao"),
            imagem_url=None,
            link_url=None,
            anuncio_id=None,
            limite_exibicao=pk("limite_exibicao"),
            cliente_ids=pk("cliente_ids"),
            embaralhar_produtos=pk("embaralhar_produtos"),
            somente_com_desconto=pk("somente_com_desconto"),
            ordem=pk("ordem") if "ordem" in patch else row.ordem,
            ativo=pk("ativo") if "ativo" in patch else row.ativo,
            inicio_em=pk("inicio_em") if "inicio_em" in patch else row.inicio_em,
            fim_em=pk("fim_em") if "fim_em" in patch else row.fim_em,
        )
    return MarketingVitrineCardCreate(
        tipo_bloco=tipo_bloco,  # type: ignore[arg-type]
        tipo_card=tipo_card,  # type: ignore[arg-type]
        titulo=body.titulo if body.titulo is not None else row.titulo,
        descricao=body.descricao if body.descricao is not None else row.descricao,
        imagem_url=body.imagem_url if body.imagem_url is not None else row.imagem_url,
        link_url=body.link_url if body.link_url is not None else row.link_url,
        anuncio_id=None,
        anuncio_ids=None,
        limite_exibicao=None,
        cliente_ids=None,
        embaralhar_produtos=None,
        somente_com_desconto=None,
        ordem=body.ordem if body.ordem is not None else row.ordem,
        ativo=body.ativo if body.ativo is not None else row.ativo,
        inicio_em=body.inicio_em if body.inicio_em is not None else row.inicio_em,
        fim_em=body.fim_em if body.fim_em is not None else row.fim_em,
    )


@router.get("/anuncios-picklist")
def anuncios_picklist_marketing(
    q: Optional[str] = Query(None, description="Busca no título do anúncio"),
    limit: int = Query(200, ge=1, le=500),
    cliente_id: Optional[List[int]] = Query(None, description="Filtra anúncios por um ou mais CAs (clientes.id da loja)"),
    anuncio_id: Optional[List[int]] = Query(None, description="Filtra por um ou mais IDs de anúncio específicos"),
    embaralhar: bool = Query(False, description="Se true, retorna anúncios em ordem aleatória"),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    """Lista anúncios publicados (loja ativa, imagem válida) para escolher no card «Anúncio»."""
    items = listar_anuncios_picklist_vitrine(
        db,
        q,
        limit,
        cliente_ids=cliente_id,
        anuncio_ids=anuncio_id,
        embaralhar=embaralhar,
    )
    return {"items": items}


@router.get("/clientes-ca-picklist")
def clientes_ca_picklist_marketing(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    """Lista somente CAs (tenants) com loja marketplace ativa para filtros do card de anúncio."""
    rows = (
        db.query(Cliente.id, Cliente.nome)
        .join(LojaMarketplace, LojaMarketplace.cliente_id == Cliente.id)
        .filter(LojaMarketplace.status == "ativo")
        .distinct()
        .order_by(Cliente.nome.asc(), Cliente.id.asc())
        .all()
    )
    return [{"id": int(r.id), "nome": (r.nome or "").strip() or f"Cliente #{r.id}"} for r in rows]


@router.get("/vitrine-home")
def public_vitrine_home(db: Session = Depends(get_db)):
    """Payload público da home da vitrine (sem cache agressivo: no-store)."""
    payload = build_public_payload(db)
    return JSONResponse(
        content=payload,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.get("/config", response_model=MarketingVitrineConfigResponse)
def get_config_admin(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    row = get_or_create_config_row(db)
    return row


@router.patch("/config", response_model=MarketingVitrineConfigResponse)
def patch_config_admin(
    body: MarketingVitrineConfigUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    row = get_or_create_config_row(db)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_by = current_user.id
    db.commit()
    db.refresh(row)
    return row


@router.get("/cards", response_model=List[MarketingVitrineCardAdminResponse])
def list_cards_admin(
    tipo_bloco: Optional[str] = Query(
        None, description="destaque | oferta_semana | destaque_agora"
    ),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    q = db.query(MarketingVitrineCard)
    if tipo_bloco:
        q = q.filter(MarketingVitrineCard.tipo_bloco == tipo_bloco)
    rows = q.order_by(MarketingVitrineCard.tipo_bloco.asc(), MarketingVitrineCard.ordem.asc(), MarketingVitrineCard.id.desc()).all()
    return [MarketingVitrineCardAdminResponse.model_validate(r) for r in rows]


@router.post("/cards", response_model=MarketingVitrineCardAdminResponse, status_code=status.HTTP_201_CREATED)
def create_card_admin(
    body: MarketingVitrineCardCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    if body.tipo_card == "anuncio":
        ids = body.anuncio_ids or ([body.anuncio_id] if body.anuncio_id else [])
        for aid in ids:
            try:
                validar_anuncio_vinculo(db, int(aid))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
    row = MarketingVitrineCard(
        tipo_bloco=body.tipo_bloco,
        tipo_card=body.tipo_card,
        titulo=body.titulo,
        descricao=body.descricao,
        imagem_url=body.imagem_url,
        link_url=body.link_url,
        anuncio_id=body.anuncio_id,
        anuncio_ids=body.anuncio_ids if body.tipo_card == "anuncio" else None,
        limite_exibicao=body.limite_exibicao,
        cliente_ids=body.cliente_ids if body.tipo_card == "cabecalho_ofertas" else None,
        embaralhar_produtos=(
            body.embaralhar_produtos
            if (
                body.tipo_card == "cabecalho_ofertas"
                or (
                    body.tipo_card == "anuncio"
                    and body.tipo_bloco in ("oferta_semana", "destaque_agora")
                )
            )
            else None
        ),
        somente_com_desconto=body.somente_com_desconto if body.tipo_card == "cabecalho_ofertas" else None,
        ordem=body.ordem,
        ativo=body.ativo,
        inicio_em=body.inicio_em,
        fim_em=body.fim_em,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/cards/{card_id}", response_model=MarketingVitrineCardAdminResponse)
def patch_card_admin(
    card_id: int,
    body: MarketingVitrineCardUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_superadmin()),
):
    row = db.query(MarketingVitrineCard).filter(MarketingVitrineCard.id == card_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Card não encontrado")
    if not body.model_dump(exclude_unset=True):
        db.refresh(row)
        return row
    try:
        merged = _merge_card_create_from_row(row, body)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    if merged.tipo_card == "anuncio":
        ids = merged.anuncio_ids or ([merged.anuncio_id] if merged.anuncio_id else [])
        for aid in ids:
            try:
                validar_anuncio_vinculo(db, int(aid))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
    row.tipo_bloco = merged.tipo_bloco
    row.tipo_card = merged.tipo_card
    row.titulo = merged.titulo
    row.descricao = merged.descricao
    row.imagem_url = merged.imagem_url
    row.link_url = merged.link_url
    row.anuncio_id = merged.anuncio_id
    row.anuncio_ids = merged.anuncio_ids if merged.tipo_card == "anuncio" else None
    row.limite_exibicao = merged.limite_exibicao
    row.cliente_ids = merged.cliente_ids
    row.embaralhar_produtos = merged.embaralhar_produtos
    row.somente_com_desconto = merged.somente_com_desconto
    row.ordem = merged.ordem
    row.ativo = merged.ativo
    row.inicio_em = merged.inicio_em
    row.fim_em = merged.fim_em
    row.updated_by = current_user.id
    db.commit()
    db.refresh(row)
    return row


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card_admin(
    card_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_superadmin()),
):
    row = db.query(MarketingVitrineCard).filter(MarketingVitrineCard.id == card_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Card não encontrado")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
