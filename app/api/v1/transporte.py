# PDV Ibix - API Transporte (configuração de transporte da loja + regras públicas)
"""Módulo Transporte — fonte única de verdade para frete, áreas e modo de entrega da
loja na vitrine.

Atores cobertos:
- Superadministrador — altera transporte de qualquer loja (escopo amplo) e gerencia o
  modo plataforma (entregadores, custos, repasses) em outros endpoints.
- Cliente Administrador (CA) — define o transporte da própria loja: Retirada, ou Ambos
  com submodo Entrega própria (grátis / valor livre) ou Entrega plataforma.
- Consumidor (vitrine) — consome regras públicas pelo CEP no carrinho/checkout.
- Entregador — opera no modo plataforma via routers `entregador.py` e `logistica.py`.

Endpoints:
- GET   /api/v1/transporte/loja/{loja_id}                — leitura da config (CA/Superadmin).
- PATCH /api/v1/transporte/loja/{loja_id}                — atualiza modo/submodo/valores.
- GET   /api/v1/transporte/loja/{loja_id}/regras         — público (consumidor).
- GET   /api/v1/transporte/regioes-cobertura             — público: cidades ativas da plataforma.
- GET   /api/v1/transporte/loja/{loja_id}/areas[/...]    — alias somente leitura do CRUD
  de áreas (mutação continua em `marketplace.py`, mesmo `require_superadmin`).

Responsável (evolução): prazos de entrega, SLAs por região, custo do entregador por
categoria, regras de cobertura avançadas — todas devem ser adicionadas aqui, não em
`marketplace.py`. Documentar no MAPA_Frete_Transporte.md.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.middleware import forbid_cliente_access, get_cliente_scope_dep, require_permission
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models import LojaAreaEntrega, LojaMarketplace, PlataformaCidadeCobertura, Usuario
from ...schemas.marketplace import LojaAreaEntregaResponse
from ...schemas.plataforma_cidade_cobertura import PlataformaCidadeCoberturaPublic
from ...schemas.transporte import (
    TransporteConfigResponse,
    TransporteConfigUpdate,
    TransporteRegrasPublicResponse,
)
from ...services.transporte.config_service import aplicar_config_no_modelo, montar_response
from ...services.transporte.regras_service import regras_publicas_loja

router = APIRouter(prefix="/transporte", tags=["Transporte"])


@router.get(
    "/regioes-cobertura",
    response_model=List[PlataformaCidadeCoberturaPublic],
)
def listar_regioes_cobertura_publicas(db: Session = Depends(get_db)):
    """Cidades/UF ativas definidas pelo Superadmin para o marketplace.

    Sem autenticação — usado na vitrine e no painel para exibir onde há entrega autorizada.
    Se a lista estiver vazia, não há whitelist geográfica (comportamento legado).
    """
    return (
        db.query(PlataformaCidadeCobertura)
        .filter(PlataformaCidadeCobertura.ativo.is_(True))
        .order_by(PlataformaCidadeCobertura.uf, func.lower(PlataformaCidadeCobertura.cidade))
        .all()
    )


def _allowed_cliente_ids(scope: ClienteScope) -> Optional[List[int]]:
    if scope.is_superadmin or scope.see_all:
        return None
    return scope.allowed_ids or []


def _carregar_loja_no_escopo(db: Session, loja_id: int, scope: ClienteScope) -> LojaMarketplace:
    loja = db.query(LojaMarketplace).filter(LojaMarketplace.id == loja_id).first()
    if not loja:
        raise HTTPException(status_code=404, detail="Loja não encontrada")
    allowed = _allowed_cliente_ids(scope)
    if allowed is not None and loja.cliente_id not in allowed:
        raise HTTPException(status_code=403, detail="Loja fora do escopo")
    return loja


@router.get("/loja/{loja_id}", response_model=TransporteConfigResponse)
def obter_config_transporte(
    loja_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Retorna configuração de transporte da loja (escopo: própria loja do CA ou qualquer loja
    para Superadmin/Administrador com escopo amplo)."""
    loja = _carregar_loja_no_escopo(db, loja_id, scope)
    return montar_response(loja)


@router.patch("/loja/{loja_id}", response_model=TransporteConfigResponse)
def atualizar_config_transporte(
    loja_id: int,
    body: TransporteConfigUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:configurar_loja")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Atualiza modo/submodo/valores de transporte da loja.

    Hierarquia:
    - **CA** salva apenas a própria loja (filtro por escopo).
    - **Superadministrador / Administrador** com escopo amplo: qualquer loja.

    SEO avançado, slug e demais campos da loja continuam em `PATCH /api/v1/marketplace/loja/{id}`.
    """
    loja = _carregar_loja_no_escopo(db, loja_id, scope)
    aplicar_config_no_modelo(loja, body)
    db.commit()
    db.refresh(loja)
    return montar_response(loja)


@router.get("/loja/{loja_id}/regras", response_model=TransporteRegrasPublicResponse)
def regras_publicas_transporte(
    loja_id: int,
    cidade: Optional[str] = Query(None, description="Cidade do consumidor (ViaCEP)"),
    uf: Optional[str] = Query(None, max_length=2, description="UF do consumidor (2 letras)"),
    db: Session = Depends(get_db),
):
    """Regras públicas (sem auth) para consumo do carrinho/checkout da vitrine.

    Mantém o mesmo contrato do legado `GET /api/v1/loja/{id}/frete`, que vira alias e
    delega para este handler. Migrar os fetches da vitrine para esta URL.
    """
    return regras_publicas_loja(db, loja_id, cidade=cidade, uf=uf)


@router.get(
    "/loja/{loja_id}/areas",
    response_model=List[LojaAreaEntregaResponse],
)
def listar_areas_transporte(
    loja_id: int,
    ativo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    _: None = Depends(forbid_cliente_access),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Alias somente leitura para áreas de entrega da loja.

    Mutação (POST/PATCH/DELETE) permanece em `/api/v1/marketplace/loja/{id}/areas-entrega`
    com `require_superadmin()` — sem mudança de permissão.
    """
    loja = _carregar_loja_no_escopo(db, loja_id, scope)
    q = db.query(LojaAreaEntrega).filter(LojaAreaEntrega.loja_id == loja.id)
    if ativo is not None:
        q = q.filter(LojaAreaEntrega.ativo == ativo)
    return q.order_by(LojaAreaEntrega.cidade).all()
