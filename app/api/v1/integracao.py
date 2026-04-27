# PDV Ibix - API de integração CRM (pull por token Bearer)
"""Endpoints GET para CRM externo: consumidores, pedidos, eventos. Auth via Bearer (INTEGRATION_TOKEN)."""
import base64
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...database.connection import get_db
from ...models import (
    ConsumidorMarketplace,
    IntegrationEvent,
    PedidoItemMarketplace,
    PedidoMarketplace,
)

router = APIRouter(prefix="/integracao", tags=["Integração CRM"])

INTEGRATION_TOKEN_ENV = "INTEGRATION_TOKEN"


def _get_integration_token() -> Optional[str]:
    return os.environ.get(INTEGRATION_TOKEN_ENV, "").strip() or None


async def require_integration_token(authorization: Optional[str] = Header(None, alias="Authorization")) -> None:
    """Dependency: exige Bearer token igual a INTEGRATION_TOKEN."""
    token = _get_integration_token()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integração não configurada (INTEGRATION_TOKEN)",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token obrigatório",
            headers={"WWW-Authenticate": "Bearer"},
        )
    candidate = authorization[7:].strip()
    if candidate != token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token inválido")


# --- Schemas resposta ---
class ConsumerOut(BaseModel):
    id: int
    tenant_id: Optional[int]
    email: str
    nome: str
    telefone: Optional[str]
    documento: Optional[str]
    tipo_consumidor: str
    status_cadastro: str
    aceite_marketing: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class OrderItemOut(BaseModel):
    id: int
    nome_produto_snapshot: Optional[str]
    quantidade: int
    preco_unitario: float
    preco_total: float

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    numero_pedido: str
    tenant_id: int
    loja_id: int
    comprador_id: Optional[int]
    total: float
    status_pedido: str
    status_pagamento: str
    status_entrega: str
    created_at: Optional[str]
    itens: List[OrderItemOut] = []

    class Config:
        from_attributes = True


class EventOut(BaseModel):
    id: int
    tenant_id: int
    event_name: str
    entity_type: str
    entity_id: int
    payload_json: dict
    status: str
    created_at: Optional[str]

    class Config:
        from_attributes = True


class CursorPage(BaseModel):
    items: List
    next_cursor: Optional[str] = None
    limit: int


def _decode_cursor(cursor: Optional[str], default_id: int = 0) -> int:
    if not cursor:
        return default_id
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        return int(raw.decode())
    except Exception:
        return default_id


def _encode_cursor(last_id: int) -> str:
    return base64.urlsafe_b64encode(str(last_id).encode()).decode()


# --- Health ---
@router.get("/health")
async def integracao_health(_: None = Depends(require_integration_token)):
    """Health check da API de integração (requer Bearer)."""
    return {"status": "ok", "message": "Integration API"}


# --- Consumidores ---
@router.get("/consumidores", response_model=CursorPage)
async def listar_consumidores(
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None),
    tenant_id: Optional[int] = Query(None),
    tipo_consumidor: Optional[str] = Query(None),
    status_cadastro: Optional[str] = Query(None),
    updated_after: Optional[str] = Query(None),
    created_after: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: None = Depends(require_integration_token),
):
    """Lista consumidores com paginação por cursor."""
    from datetime import datetime
    q = db.query(ConsumidorMarketplace).filter(ConsumidorMarketplace.deleted_at.is_(None))
    last_id = _decode_cursor(cursor)
    q = q.filter(ConsumidorMarketplace.id > last_id)
    if tenant_id is not None:
        q = q.filter(ConsumidorMarketplace.tenant_id == tenant_id)
    if tipo_consumidor:
        q = q.filter(ConsumidorMarketplace.tipo_consumidor == tipo_consumidor)
    if status_cadastro:
        q = q.filter(ConsumidorMarketplace.status_cadastro == status_cadastro)
    if updated_after:
        try:
            dt = datetime.fromisoformat(updated_after.replace("Z", "+00:00"))
            q = q.filter(ConsumidorMarketplace.updated_at >= dt)
        except Exception:
            pass
    if created_after:
        try:
            dt = datetime.fromisoformat(created_after.replace("Z", "+00:00"))
            q = q.filter(ConsumidorMarketplace.created_at >= dt)
        except Exception:
            pass
    q = q.order_by(ConsumidorMarketplace.id).limit(limit + 1)
    rows = q.all()
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    next_cursor = _encode_cursor(rows[-1].id) if rows and has_more else None
    items = [
        ConsumerOut(
            id=r.id,
            tenant_id=r.tenant_id,
            email=r.email,
            nome=r.nome,
            telefone=r.telefone,
            documento=r.documento,
            tipo_consumidor=r.tipo_consumidor or "",
            status_cadastro=r.status_cadastro or "",
            aceite_marketing=getattr(r, "aceite_marketing", False),
            created_at=r.created_at.isoformat() if r.created_at else None,
            updated_at=r.updated_at.isoformat() if getattr(r, "updated_at", None) else None,
        )
        for r in rows
    ]
    return CursorPage(items=items, next_cursor=next_cursor, limit=limit)


@router.get("/consumidores/{consumer_id}", response_model=ConsumerOut)
async def obter_consumidor(
    consumer_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_integration_token),
):
    """Retorna um consumidor por ID."""
    r = db.query(ConsumidorMarketplace).filter(
        ConsumidorMarketplace.id == consumer_id,
        ConsumidorMarketplace.deleted_at.is_(None),
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Consumidor não encontrado")
    return ConsumerOut(
        id=r.id,
        tenant_id=r.tenant_id,
        email=r.email,
        nome=r.nome,
        telefone=r.telefone,
        documento=r.documento,
        tipo_consumidor=r.tipo_consumidor or "",
        status_cadastro=r.status_cadastro or "",
        aceite_marketing=getattr(r, "aceite_marketing", False),
        created_at=r.created_at.isoformat() if r.created_at else None,
        updated_at=r.updated_at.isoformat() if getattr(r, "updated_at", None) else None,
    )


# --- Pedidos ---
@router.get("/pedidos", response_model=CursorPage)
async def listar_pedidos(
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None),
    tenant_id: Optional[int] = Query(None),
    status_pagamento: Optional[str] = Query(None),
    created_after: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: None = Depends(require_integration_token),
):
    """Lista pedidos com paginação por cursor."""
    from datetime import datetime
    q = db.query(PedidoMarketplace).order_by(PedidoMarketplace.id)
    last_id = _decode_cursor(cursor)
    q = q.filter(PedidoMarketplace.id > last_id)
    if tenant_id is not None:
        q = q.filter(PedidoMarketplace.tenant_id == tenant_id)
    if status_pagamento:
        q = q.filter(PedidoMarketplace.status_pagamento == status_pagamento)
    if created_after:
        try:
            dt = datetime.fromisoformat(created_after.replace("Z", "+00:00"))
            q = q.filter(PedidoMarketplace.created_at >= dt)
        except Exception:
            pass
    q = q.limit(limit + 1)
    rows = q.all()
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    next_cursor = _encode_cursor(rows[-1].id) if rows and has_more else None
    items = []
    for p in rows:
        itens = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == p.id).all()
        items.append(
            OrderOut(
                id=p.id,
                numero_pedido=p.numero_pedido,
                tenant_id=p.tenant_id,
                loja_id=p.loja_id,
                comprador_id=p.comprador_id,
                total=float(p.total),
                status_pedido=p.status_pedido or "",
                status_pagamento=p.status_pagamento or "",
                status_entrega=getattr(p, "status_entrega", "") or "pendente",
                created_at=p.created_at.isoformat() if p.created_at else None,
                itens=[
                    OrderItemOut(
                        id=i.id,
                        nome_produto_snapshot=getattr(i, "nome_produto_snapshot", None),
                        quantidade=i.quantidade,
                        preco_unitario=float(i.preco_unitario or 0),
                        preco_total=float(i.preco_total or 0),
                    )
                    for i in itens
                ],
            )
        )
    return CursorPage(items=items, next_cursor=next_cursor, limit=limit)


@router.get("/pedidos/{order_id}", response_model=OrderOut)
async def obter_pedido(
    order_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_integration_token),
):
    """Retorna um pedido por ID com itens."""
    p = db.query(PedidoMarketplace).filter(PedidoMarketplace.id == order_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    itens = db.query(PedidoItemMarketplace).filter(PedidoItemMarketplace.pedido_id == p.id).all()
    return OrderOut(
        id=p.id,
        numero_pedido=p.numero_pedido,
        tenant_id=p.tenant_id,
        loja_id=p.loja_id,
        comprador_id=p.comprador_id,
        total=float(p.total),
        status_pedido=p.status_pedido or "",
        status_pagamento=p.status_pagamento or "",
        status_entrega=getattr(p, "status_entrega", "") or "pendente",
        created_at=p.created_at.isoformat() if p.created_at else None,
        itens=[
            OrderItemOut(
                id=i.id,
                nome_produto_snapshot=getattr(i, "nome_produto_snapshot", None),
                quantidade=i.quantidade,
                preco_unitario=float(i.preco_unitario or 0),
                preco_total=float(i.preco_total or 0),
            )
            for i in itens
        ],
    )


# --- Eventos ---
@router.get("/eventos", response_model=CursorPage)
async def listar_eventos(
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None),
    tenant_id: Optional[int] = Query(None),
    event_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    created_after: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: None = Depends(require_integration_token),
):
    """Lista eventos de integração com paginação por cursor."""
    from datetime import datetime
    q = db.query(IntegrationEvent).order_by(IntegrationEvent.id)
    last_id = _decode_cursor(cursor)
    q = q.filter(IntegrationEvent.id > last_id)
    if tenant_id is not None:
        q = q.filter(IntegrationEvent.tenant_id == tenant_id)
    if event_name:
        q = q.filter(IntegrationEvent.event_name == event_name)
    if status:
        q = q.filter(IntegrationEvent.status == status)
    if created_after:
        try:
            dt = datetime.fromisoformat(created_after.replace("Z", "+00:00"))
            q = q.filter(IntegrationEvent.created_at >= dt)
        except Exception:
            pass
    q = q.limit(limit + 1)
    rows = q.all()
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    next_cursor = _encode_cursor(rows[-1].id) if rows and has_more else None
    items = [
        EventOut(
            id=r.id,
            tenant_id=r.tenant_id,
            event_name=r.event_name,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            payload_json=dict(r.payload_json) if r.payload_json else {},
            status=r.status,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]
    return CursorPage(items=items, next_cursor=next_cursor, limit=limit)
