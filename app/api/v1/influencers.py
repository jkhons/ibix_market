# PDV Ibix - API Influencers / Marketing
"""CRUD influencers, campanhas, links e metricas. Unifica representantes e influencers."""
import secrets
import string
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ...core.audit import audit_action
from ...core.middleware import get_current_user, require_superadmin, require_superadmin_or_admin
from ...core.scope import resolve_tenant_pagador
from ...database.connection import get_db
from ...models import Usuario
from ...models.codigo_desconto import CodigoDesconto
from ...models.divulgador import Divulgador
from ...models.influencer_campanha import InfluencerCampanha
from ...models.influencer_link import InfluencerLink
from ...models.influencer_metrica import InfluencerMetrica
from ...schemas.influencer import (
    CampanhaCreate,
    CampanhaResponse,
    CampanhaUpdate,
    InfluencerResponse,
    InfluencerStatusUpdate,
    InfluencerUpdate,
    LinkCreate,
    LinkResponse,
    MetricaAgregada,
    MetricaResponse,
)

router = APIRouter(tags=["Influencers"])


VALID_STATUS = ("pendente", "teste", "aprovado", "parceiro", "bloqueado")
VALID_TIPOS = ("representante", "influencer", "parceiro")
VALID_CAMPANHA_TIPOS = ("propaganda", "cupom", "live")
VALID_CAMPANHA_STATUS = ("rascunho", "ativa", "pausada", "finalizada", "cancelada")


def _get_divulgador_by_user(db: Session, user: Usuario) -> Divulgador:
    div = db.query(Divulgador).filter(Divulgador.usuario_id == user.id).first()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil de influencer não encontrado para este usuário.")
    return div


def _is_influencer(user: Usuario) -> bool:
    return bool(user.role and user.role.nome == "Influencer")


def _is_superadmin(user: Usuario) -> bool:
    return bool(user.role and user.role.nome == "Superadministrador")


def _is_ca(user: Usuario) -> bool:
    return bool(user.role and user.role.nome == "Cliente Administrador")


def _generate_cupom_code(nome: str) -> str:
    slug = "".join(c for c in nome.upper().split()[0] if c.isalpha())[:8]
    suffix = "".join(secrets.choice(string.digits) for _ in range(3))
    return f"{slug}{suffix}"


def _generate_tracking_code() -> str:
    return "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(12))


# ── Influencer: endpoints proprios (/me) ────────────────────────────────

@router.get("/influencers/me", response_model=InfluencerResponse)
def meu_perfil(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if not _is_influencer(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a influencers.")
    return _get_divulgador_by_user(db, current_user)


@router.get("/influencers/me/campanhas", response_model=List[CampanhaResponse])
def minhas_campanhas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if not _is_influencer(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a influencers.")
    div = _get_divulgador_by_user(db, current_user)
    campanhas = (
        db.query(InfluencerCampanha)
        .options(joinedload(InfluencerCampanha.codigo_desconto))
        .filter(InfluencerCampanha.divulgador_id == div.id)
        .order_by(InfluencerCampanha.created_at.desc())
        .all()
    )
    return [_campanha_to_response(c) for c in campanhas]


@router.get("/influencers/me/metricas", response_model=MetricaAgregada)
def minhas_metricas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if not _is_influencer(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a influencers.")
    div = _get_divulgador_by_user(db, current_user)
    row = db.query(
        func.coalesce(func.sum(InfluencerMetrica.cliques), 0).label("total_cliques"),
        func.coalesce(func.sum(InfluencerMetrica.vendas), 0).label("total_vendas"),
        func.coalesce(func.sum(InfluencerMetrica.faturamento), 0).label("total_faturamento"),
        func.coalesce(func.sum(InfluencerMetrica.conversoes_cupom), 0).label("total_conversoes_cupom"),
    ).filter(InfluencerMetrica.divulgador_id == div.id).first()
    total_campanhas = db.query(func.count(InfluencerCampanha.id)).filter(InfluencerCampanha.divulgador_id == div.id).scalar()
    return MetricaAgregada(
        total_cliques=row.total_cliques,
        total_vendas=row.total_vendas,
        total_faturamento=Decimal(str(row.total_faturamento)),
        total_conversoes_cupom=row.total_conversoes_cupom,
        total_campanhas=total_campanhas or 0,
    )


@router.get("/influencers/me/links", response_model=List[LinkResponse])
def meus_links(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if not _is_influencer(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a influencers.")
    div = _get_divulgador_by_user(db, current_user)
    links = db.query(InfluencerLink).filter(InfluencerLink.divulgador_id == div.id, InfluencerLink.ativo == True).all()
    return [_link_to_response(lnk) for lnk in links]


@router.get("/influencers/me/cupons")
def meus_cupons(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if not _is_influencer(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a influencers.")
    div = _get_divulgador_by_user(db, current_user)
    cupons = db.query(CodigoDesconto).filter(CodigoDesconto.divulgador_id == div.id, CodigoDesconto.ativo == True).all()
    return [{"id": c.id, "codigo": c.codigo, "tipo_promocao": c.tipo_promocao, "ativo": c.ativo} for c in cupons]


# ── Admin: CRUD influencers ─────────────────────────────────────────────

@router.get("/influencers", response_model=List[InfluencerResponse])
def listar_influencers(
    tipo: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    nicho: Optional[str] = Query(None),
    cidade: Optional[str] = Query(None),
    ativo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin_or_admin()),
):
    q = db.query(Divulgador)
    if tipo:
        q = q.filter(Divulgador.tipo == tipo)
    if status_filter:
        q = q.filter(Divulgador.status == status_filter)
    if nicho:
        q = q.filter(Divulgador.nicho.ilike(f"%{nicho}%"))
    if cidade:
        q = q.filter(Divulgador.cidade.ilike(f"%{cidade}%"))
    if ativo is not None:
        q = q.filter(Divulgador.ativo == ativo)
    return q.order_by(Divulgador.score_performance.desc().nullslast(), Divulgador.nome).all()


@router.get("/influencers/{div_id}", response_model=InfluencerResponse)
def detalhe_influencer(
    div_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin_or_admin()),
):
    div = db.query(Divulgador).filter(Divulgador.id == div_id).first()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer não encontrado")
    return div


@router.patch("/influencers/{div_id}", response_model=InfluencerResponse)
def atualizar_influencer(
    div_id: int,
    body: InfluencerUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin()),
):
    div = db.query(Divulgador).filter(Divulgador.id == div_id).first()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer não encontrado")
    update_data = body.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(div, field, val)
    db.commit()
    db.refresh(div)
    audit_action(
        db, "influencer_atualizado",
        user_id=current_user.id,
        tenant_id=resolve_tenant_pagador(db, current_user.id, current_user.role.nome if current_user.role else None),
        recurso_tipo="divulgador", recurso_id=div.id,
    )
    return div


@router.patch("/influencers/{div_id}/status", response_model=InfluencerResponse)
def alterar_status_influencer(
    div_id: int,
    body: InfluencerStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin()),
):
    if body.status not in VALID_STATUS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Status inválido. Valores: {', '.join(VALID_STATUS)}")
    div = db.query(Divulgador).filter(Divulgador.id == div_id).first()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer não encontrado")
    old_status = div.status
    div.status = body.status
    db.commit()
    db.refresh(div)
    audit_action(
        db, "influencer_status_alterado",
        user_id=current_user.id,
        tenant_id=resolve_tenant_pagador(db, current_user.id, current_user.role.nome if current_user.role else None),
        recurso_tipo="divulgador", recurso_id=div.id,
        detalhes=f"{old_status} -> {body.status}" + (f" motivo={body.motivo}" if body.motivo else ""),
    )
    try:
        from ...services.influencer_notification_service import notificar_status_alterado
        notificar_status_alterado(db, div, body.status, current_user.id)
    except Exception:
        pass
    return div


@router.delete("/influencers/{div_id}")
def desativar_influencer(
    div_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin()),
):
    div = db.query(Divulgador).filter(Divulgador.id == div_id).first()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer não encontrado")
    div.ativo = False
    div.status = "bloqueado"
    db.commit()
    return {"detail": "Influencer desativado"}


# ── Influencers disponiveis (para CA) ───────────────────────────────────

@router.get("/influencers/disponiveis", response_model=List[InfluencerResponse])
def listar_disponiveis(
    nicho: Optional[str] = Query(None),
    cidade: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    q = db.query(Divulgador).filter(
        Divulgador.ativo == True,
        Divulgador.tipo == "influencer",
        Divulgador.status.in_(("aprovado", "parceiro")),
    )
    if nicho:
        q = q.filter(Divulgador.nicho.ilike(f"%{nicho}%"))
    if cidade:
        q = q.filter(Divulgador.cidade.ilike(f"%{cidade}%"))
    return q.order_by(Divulgador.score_performance.desc().nullslast()).all()


# ── Campanhas ────────────────────────────────────────────────────────────

def _campanha_to_response(c: InfluencerCampanha) -> CampanhaResponse:
    data = CampanhaResponse.model_validate(c).model_dump()
    data["influencer_nome"] = c.divulgador.nome if c.divulgador else None
    data["cupom_codigo"] = c.codigo_desconto.codigo if c.codigo_desconto else None
    return CampanhaResponse(**data)


@router.get("/influencers/campanhas", response_model=List[CampanhaResponse])
def listar_campanhas(
    status_filter: Optional[str] = Query(None, alias="status"),
    tipo: Optional[str] = Query(None),
    divulgador_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    q = (
        db.query(InfluencerCampanha)
        .options(
            joinedload(InfluencerCampanha.divulgador),
            joinedload(InfluencerCampanha.codigo_desconto),
        )
    )
    if _is_ca(current_user):
        from ...models.loja_marketplace import LojaMarketplace
        loja = db.query(LojaMarketplace).filter(LojaMarketplace.cliente_id == current_user.id).first()
        if loja:
            q = q.filter(InfluencerCampanha.loja_id == loja.id)
        else:
            return []
    elif _is_influencer(current_user):
        div = _get_divulgador_by_user(db, current_user)
        q = q.filter(InfluencerCampanha.divulgador_id == div.id)
    if status_filter:
        q = q.filter(InfluencerCampanha.status == status_filter)
    if tipo:
        q = q.filter(InfluencerCampanha.tipo == tipo)
    if divulgador_id:
        q = q.filter(InfluencerCampanha.divulgador_id == divulgador_id)
    campanhas = q.order_by(InfluencerCampanha.created_at.desc()).all()
    return [_campanha_to_response(c) for c in campanhas]


@router.post("/influencers/campanhas", response_model=CampanhaResponse, status_code=status.HTTP_201_CREATED)
def criar_campanha(
    body: CampanhaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if not (_is_superadmin(current_user) or _is_ca(current_user)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas Super Admin ou Cliente Administrador podem criar campanhas.")
    if body.tipo not in VALID_CAMPANHA_TIPOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tipo inválido. Valores: {', '.join(VALID_CAMPANHA_TIPOS)}")
    div = db.query(Divulgador).filter(Divulgador.id == body.divulgador_id).first()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer não encontrado")

    codigo_desconto_id = body.codigo_desconto_id

    if body.tipo == "cupom" and not codigo_desconto_id:
        codigo = _generate_cupom_code(div.nome)
        for _ in range(10):
            if not db.query(CodigoDesconto).filter(CodigoDesconto.codigo == codigo).first():
                break
            codigo = _generate_cupom_code(div.nome)
        cupom = CodigoDesconto(
            codigo=codigo,
            tipo_promocao="desconto_mensalidade",
            desconto_mensalidade_percent=10,
            ativo=True,
            divulgador_id=div.id,
        )
        db.add(cupom)
        db.flush()
        codigo_desconto_id = cupom.id

    campanha = InfluencerCampanha(
        divulgador_id=body.divulgador_id,
        loja_id=body.loja_id,
        titulo=body.titulo,
        descricao=body.descricao,
        tipo=body.tipo,
        status="ativa" if not body.is_teste else "ativa",
        data_inicio=body.data_inicio,
        data_fim=body.data_fim,
        valor_fixo=body.valor_fixo,
        percentual_comissao=body.percentual_comissao,
        modelo_pagamento=body.modelo_pagamento,
        codigo_desconto_id=codigo_desconto_id,
        is_teste=body.is_teste,
    )
    db.add(campanha)
    db.commit()
    db.refresh(campanha)
    audit_action(
        db, "influencer_campanha_criada",
        user_id=current_user.id,
        tenant_id=resolve_tenant_pagador(db, current_user.id, current_user.role.nome if current_user.role else None),
        recurso_tipo="influencer_campanha", recurso_id=campanha.id,
    )
    try:
        from ...services.influencer_notification_service import notificar_nova_campanha
        notificar_nova_campanha(db, div, campanha, current_user.id)
    except Exception:
        pass
    db.refresh(campanha)
    campanha_loaded = (
        db.query(InfluencerCampanha)
        .options(joinedload(InfluencerCampanha.divulgador), joinedload(InfluencerCampanha.codigo_desconto))
        .filter(InfluencerCampanha.id == campanha.id)
        .first()
    )
    return _campanha_to_response(campanha_loaded)


@router.patch("/influencers/campanhas/{campanha_id}", response_model=CampanhaResponse)
def atualizar_campanha(
    campanha_id: int,
    body: CampanhaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if not (_is_superadmin(current_user) or _is_ca(current_user)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão.")
    campanha = (
        db.query(InfluencerCampanha)
        .options(joinedload(InfluencerCampanha.divulgador), joinedload(InfluencerCampanha.codigo_desconto))
        .filter(InfluencerCampanha.id == campanha_id)
        .first()
    )
    if not campanha:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campanha não encontrada")
    if body.status and body.status not in VALID_CAMPANHA_STATUS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Status inválido. Valores: {', '.join(VALID_CAMPANHA_STATUS)}")
    update_data = body.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(campanha, field, val)
    db.commit()
    db.refresh(campanha)
    return _campanha_to_response(campanha)


# ── Links rastreaveis ────────────────────────────────────────────────────

def _link_to_response(lnk: InfluencerLink) -> LinkResponse:
    data = LinkResponse.model_validate(lnk).model_dump()
    data["url_rastreavel"] = f"/i/{lnk.codigo_rastreio}"
    return LinkResponse(**data)


@router.get("/influencers/campanhas/{campanha_id}/links", response_model=List[LinkResponse])
def listar_links_campanha(
    campanha_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    links = db.query(InfluencerLink).filter(InfluencerLink.campanha_id == campanha_id, InfluencerLink.ativo == True).all()
    return [_link_to_response(lnk) for lnk in links]


@router.post("/influencers/campanhas/{campanha_id}/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
def criar_link(
    campanha_id: int,
    body: LinkCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if not (_is_superadmin(current_user) or _is_ca(current_user)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão.")
    campanha = db.query(InfluencerCampanha).filter(InfluencerCampanha.id == campanha_id).first()
    if not campanha:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campanha não encontrada")
    codigo = _generate_tracking_code()
    for _ in range(10):
        if not db.query(InfluencerLink).filter(InfluencerLink.codigo_rastreio == codigo).first():
            break
        codigo = _generate_tracking_code()
    lnk = InfluencerLink(
        campanha_id=campanha_id,
        divulgador_id=body.divulgador_id,
        url_destino=body.url_destino,
        codigo_rastreio=codigo,
        ativo=True,
    )
    db.add(lnk)
    db.commit()
    db.refresh(lnk)
    return _link_to_response(lnk)


# ── Metricas ─────────────────────────────────────────────────────────────

@router.get("/influencers/{div_id}/metricas", response_model=MetricaAgregada)
def metricas_influencer(
    div_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    div = db.query(Divulgador).filter(Divulgador.id == div_id).first()
    if not div:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer não encontrado")
    row = db.query(
        func.coalesce(func.sum(InfluencerMetrica.cliques), 0).label("total_cliques"),
        func.coalesce(func.sum(InfluencerMetrica.vendas), 0).label("total_vendas"),
        func.coalesce(func.sum(InfluencerMetrica.faturamento), 0).label("total_faturamento"),
        func.coalesce(func.sum(InfluencerMetrica.conversoes_cupom), 0).label("total_conversoes_cupom"),
    ).filter(InfluencerMetrica.divulgador_id == div_id).first()
    total_campanhas = db.query(func.count(InfluencerCampanha.id)).filter(InfluencerCampanha.divulgador_id == div_id).scalar()
    return MetricaAgregada(
        total_cliques=row.total_cliques,
        total_vendas=row.total_vendas,
        total_faturamento=Decimal(str(row.total_faturamento)),
        total_conversoes_cupom=row.total_conversoes_cupom,
        total_campanhas=total_campanhas or 0,
    )


@router.get("/influencers/campanhas/{campanha_id}/metricas", response_model=List[MetricaResponse])
def metricas_campanha(
    campanha_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return db.query(InfluencerMetrica).filter(InfluencerMetrica.campanha_id == campanha_id).all()


# ── Recalcular scores (Super Admin) ─────────────────────────────────────

@router.post("/influencers/recalcular-scores")
def recalcular_scores(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _: None = Depends(require_superadmin()),
):
    divulgadores = db.query(Divulgador).filter(Divulgador.tipo == "influencer", Divulgador.ativo == True).all()
    updated = 0
    for div in divulgadores:
        row = db.query(
            func.coalesce(func.sum(InfluencerMetrica.vendas), 0).label("vendas"),
            func.coalesce(func.sum(InfluencerMetrica.cliques), 0).label("cliques"),
            func.coalesce(func.sum(InfluencerMetrica.conversoes_cupom), 0).label("conversoes"),
        ).filter(InfluencerMetrica.divulgador_id == div.id).first()
        score = (row.vendas * 10) + (row.cliques * 1) + (row.conversoes * 5)
        div.score_performance = score
        updated += 1
    db.commit()
    return {"detail": f"{updated} influencers atualizados"}
