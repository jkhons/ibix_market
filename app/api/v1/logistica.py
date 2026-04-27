# PDV Ibix - API Logística (tenant: criar, publicar, listar, cancelar entregas)
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.middleware import get_cliente_scope_dep, require_permission
from ...core.scope import ClienteScope
from ...database.connection import get_db
from ...models import EntregaMarketplace, PedidoMarketplace, Usuario
from ...schemas.entrega_marketplace import EntregaCreateIn, EntregaEventoOut, EntregaOut
from ...services.logistica.entrega_service import cancelar_entrega, criar_entrega, publicar_entrega

router = APIRouter(prefix="/logistica", tags=["Logística"])


def _allowed_cliente_ids(scope: ClienteScope) -> Optional[List[int]]:
    if scope.is_superadmin or scope.see_all:
        return None
    return scope.allowed_ids or []


@router.post("/entregas", response_model=EntregaOut, status_code=status.HTTP_201_CREATED)
def criar_entrega_endpoint(
    body: EntregaCreateIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Cria entrega a partir do pedido. Pedido deve estar no escopo do tenant."""
    allowed = _allowed_cliente_ids(scope)
    pedido = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == body.pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
    if allowed is not None and pedido.tenant_id not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Pedido fora do escopo")
    try:
        entrega = criar_entrega(
            db,
            pedido_id=body.pedido_id,
            tenant_id=pedido.tenant_id,
            valor_frete=float(body.valor_frete),
            tipo_veiculo_aceito=body.tipo_veiculo_aceito,
            observacoes=body.observacoes,
            aceita_ate_em=body.aceita_ate_em,
            actor_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    data = EntregaOut.model_validate(entrega).model_dump()
    data["eventos"] = [EntregaEventoOut.model_validate(ev) for ev in entrega.eventos]
    return EntregaOut(**data)


@router.post("/entregas/{entrega_id}/publicar", response_model=EntregaOut)
def publicar_entrega_endpoint(
    entrega_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Publica entrega (status -> disponivel)."""
    allowed = _allowed_cliente_ids(scope)
    entrega = db.query(EntregaMarketplace).filter(EntregaMarketplace.id == entrega_id).first()
    if not entrega:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrega não encontrada")
    if allowed is not None and entrega.tenant_id not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Entrega fora do escopo")
    try:
        entrega = publicar_entrega(db, entrega_id, actor_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    data = EntregaOut.model_validate(entrega).model_dump()
    data["eventos"] = [EntregaEventoOut.model_validate(ev) for ev in entrega.eventos]
    return EntregaOut(**data)


@router.get("/entregas", response_model=List[EntregaOut])
def listar_entregas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Lista entregas do escopo do tenant."""
    allowed = _allowed_cliente_ids(scope)
    q = db.query(EntregaMarketplace).order_by(EntregaMarketplace.created_at.desc())
    if allowed is not None:
        q = q.filter(EntregaMarketplace.tenant_id.in_(allowed))
    rows = q.limit(200).all()
    return [
        EntregaOut(**EntregaOut.model_validate(e).model_dump() | {"eventos": [EntregaEventoOut.model_validate(ev) for ev in e.eventos]})
        for e in rows
    ]


@router.get("/entregas/{entrega_id}", response_model=EntregaOut)
def detalhe_entrega(
    entrega_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Detalhe da entrega (com eventos)."""
    allowed = _allowed_cliente_ids(scope)
    entrega = db.query(EntregaMarketplace).filter(EntregaMarketplace.id == entrega_id).first()
    if not entrega:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrega não encontrada")
    if allowed is not None and entrega.tenant_id not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Entrega fora do escopo")
    data = EntregaOut.model_validate(entrega).model_dump()
    data["eventos"] = [EntregaEventoOut.model_validate(ev) for ev in entrega.eventos]
    return EntregaOut(**data)


@router.post("/entregas/{entrega_id}/cancelar", response_model=EntregaOut)
def cancelar_entrega_endpoint(
    entrega_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission("marketplace:visualizar")),
    scope: ClienteScope = Depends(get_cliente_scope_dep),
):
    """Cancela a entrega."""
    allowed = _allowed_cliente_ids(scope)
    entrega = db.query(EntregaMarketplace).filter(EntregaMarketplace.id == entrega_id).first()
    if not entrega:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrega não encontrada")
    if allowed is not None and entrega.tenant_id not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Entrega fora do escopo")
    try:
        entrega = cancelar_entrega(db, entrega_id, actor_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    data = EntregaOut.model_validate(entrega).model_dump()
    data["eventos"] = [EntregaEventoOut.model_validate(ev) for ev in entrega.eventos]
    return EntregaOut(**data)
