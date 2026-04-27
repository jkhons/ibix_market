# PDV Ibix - Service para cancelamento e devolução de pedidos
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.devolucao_marketplace import DevolucaoMarketplace
from app.models.motivo_cancelamento import MotivoCancelamento
from app.models.pedido_marketplace import PedidoMarketplace
from app.services.pedido_status_evento_service import registrar_pedido_status_evento
from app.services.reserva_estoque_marketplace_service import restore_marketplace_pedido_stock

STATUSES_CANCELAVEIS = {"aguardando_pagamento", "pendente", "pago", "em_preparacao"}
PRAZO_DEVOLUCAO_DIAS = 7


def cancelar_pedido(
    db: Session,
    pedido_id: int,
    consumidor_id: int,
    motivo_id: int,
    descricao: Optional[str] = None,
) -> PedidoMarketplace:
    pedido = (
        db.query(PedidoMarketplace)
        .filter(PedidoMarketplace.id == pedido_id)
        .first()
    )
    if not pedido:
        raise ValueError("PEDIDO_NOT_FOUND")
    if pedido.comprador_id != consumidor_id:
        raise PermissionError("PEDIDO_NOT_OWNED")
    if pedido.status_pedido not in STATUSES_CANCELAVEIS:
        raise ValueError("ORDER_NOT_CANCELLABLE")

    motivo = db.query(MotivoCancelamento).filter(MotivoCancelamento.id == motivo_id).first()
    if not motivo:
        raise ValueError("MOTIVO_NOT_FOUND")

    pedido.status_pedido = "cancelado"
    registrar_pedido_status_evento(
        db,
        pedido_id=pedido.id,
        tipo_evento="cancelamento",
        status_codigo="cancelado",
        status_label=f"Cancelado: {motivo.descricao}",
        detalhes=descricao,
    )
    restore_marketplace_pedido_stock(db, pedido.id)
    db.commit()
    db.refresh(pedido)
    return pedido


def criar_devolucao(
    db: Session,
    pedido_id: int,
    consumidor_id: int,
    motivo_id: int,
    tipo: str,
    descricao: Optional[str] = None,
    fotos: Optional[list] = None,
) -> DevolucaoMarketplace:
    pedido = (
        db.query(PedidoMarketplace)
        .filter(PedidoMarketplace.id == pedido_id)
        .first()
    )
    if not pedido:
        raise ValueError("PEDIDO_NOT_FOUND")
    if pedido.comprador_id != consumidor_id:
        raise PermissionError("PEDIDO_NOT_OWNED")
    if pedido.status_pedido != "entregue":
        raise ValueError("ORDER_NOT_RETURNABLE")

    base_date = pedido.updated_at if pedido.updated_at else pedido.created_at
    limite = base_date + timedelta(days=PRAZO_DEVOLUCAO_DIAS)
    limite_utc = limite.replace(tzinfo=timezone.utc) if limite.tzinfo is None else limite
    if datetime.now(timezone.utc) > limite_utc:
        raise ValueError("RETURN_PERIOD_EXPIRED")

    existente = (
        db.query(DevolucaoMarketplace)
        .filter(
            DevolucaoMarketplace.pedido_id == pedido_id,
            DevolucaoMarketplace.status.in_(["aberta", "em_analise"]),
        )
        .first()
    )
    if existente:
        raise ValueError("RETURN_ALREADY_OPEN")

    dev = DevolucaoMarketplace(
        pedido_id=pedido_id,
        consumidor_id=consumidor_id,
        motivo_id=motivo_id,
        tipo=tipo,
        descricao=descricao,
        fotos_json=fotos,
    )
    db.add(dev)
    registrar_pedido_status_evento(
        db,
        pedido_id=pedido.id,
        tipo_evento="devolucao",
        status_codigo="devolucao_aberta",
        status_label="Solicitação de devolução aberta",
    )
    db.commit()
    db.refresh(dev)
    return dev


def consultar_devolucao(
    db: Session,
    pedido_id: int,
    consumidor_id: int,
) -> Optional[DevolucaoMarketplace]:
    return (
        db.query(DevolucaoMarketplace)
        .filter(
            DevolucaoMarketplace.pedido_id == pedido_id,
            DevolucaoMarketplace.consumidor_id == consumidor_id,
        )
        .order_by(DevolucaoMarketplace.created_at.desc())
        .first()
    )


def responder_devolucao(
    db: Session,
    devolucao_id: int,
    respondido_por: int,
    status: str,
    resposta: Optional[str] = None,
    valor_reembolso: Optional[Decimal] = None,
) -> DevolucaoMarketplace:
    dev = db.query(DevolucaoMarketplace).filter(DevolucaoMarketplace.id == devolucao_id).first()
    if not dev:
        raise ValueError("DEVOLUCAO_NOT_FOUND")
    if dev.status in ("finalizada", "recusada") and status not in ("finalizada",):
        raise ValueError("RETURN_INVALID_STATUS")

    dev.status = status
    dev.resposta_loja = resposta
    dev.respondido_por = respondido_por
    dev.respondido_em = datetime.now(timezone.utc)
    if valor_reembolso is not None:
        dev.valor_reembolso = valor_reembolso

    registrar_pedido_status_evento(
        db,
        pedido_id=dev.pedido_id,
        tipo_evento="devolucao",
        status_codigo=f"devolucao_{status}",
        status_label=f"Devolução {status}",
    )
    db.commit()
    db.refresh(dev)
    return dev
