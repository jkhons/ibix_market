# PDV Ibix - API Cancelamento e Devolução para consumidor mobile
"""Cancelar pedido, solicitar devolução, consultar motivos — requer consumidor autenticado."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...core.error_codes import (
    DEVOLUCAO_JA_ABERTA,
    DEVOLUCAO_PRAZO_EXPIRADO,
    PEDIDO_NAO_CANCELAVEL,
    PEDIDO_NAO_ENCONTRADO,
    PEDIDO_NAO_RETORNAVEL,
)
from ...database.connection import get_db
from ...models.motivo_cancelamento import MotivoCancelamento
from ...schemas.mobile import (
    CancelarPedidoRequest,
    DevolucaoCreateRequest,
    DevolucaoResponse,
    MotivoResponse,
)
from ...services.devolucao_service import (
    cancelar_pedido,
    consultar_devolucao,
    criar_devolucao,
)
from .loja import get_current_consumidor

router = APIRouter(prefix="/loja", tags=["Loja – Cancelamento/Devolução"])


def _error(status_code: int, detail: str, code: str):
    raise HTTPException(status_code=status_code, detail={"detail": detail, "code": code})


@router.post("/pedidos/{pedido_id}/cancelar")
async def cancelar_pedido_endpoint(
    pedido_id: int,
    body: CancelarPedidoRequest,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    """Cancela um pedido (se status permitir)."""
    try:
        pedido = cancelar_pedido(
            db,
            pedido_id=pedido_id,
            consumidor_id=consumidor.id,
            motivo_id=body.motivo_id,
            descricao=body.descricao_adicional,
        )
    except ValueError as e:
        msg = str(e)
        error_map = {
            "PEDIDO_NOT_FOUND": (404, "Pedido não encontrado", PEDIDO_NAO_ENCONTRADO),
            "ORDER_NOT_CANCELLABLE": (400, "Pedido não pode ser cancelado neste status", PEDIDO_NAO_CANCELAVEL),
            "MOTIVO_NOT_FOUND": (400, "Motivo não encontrado", "MOTIVO_NOT_FOUND"),
        }
        if msg in error_map:
            sc, detail, code = error_map[msg]
            _error(sc, detail, code)
        _error(400, msg, msg)
    except PermissionError:
        _error(403, "Pedido não pertence a este consumidor", "PEDIDO_NOT_OWNED")
    return {"status": "cancelado", "pedido_id": pedido.id}


@router.post("/pedidos/{pedido_id}/devolucao", status_code=201)
async def criar_devolucao_endpoint(
    pedido_id: int,
    body: DevolucaoCreateRequest,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    """Solicita devolução/reembolso de um pedido entregue (até 7 dias)."""
    try:
        dev = criar_devolucao(
            db,
            pedido_id=pedido_id,
            consumidor_id=consumidor.id,
            motivo_id=body.motivo_id,
            tipo=body.tipo,
            descricao=body.descricao,
            fotos=body.fotos,
        )
    except ValueError as e:
        msg = str(e)
        error_map = {
            "PEDIDO_NOT_FOUND": (404, "Pedido não encontrado", PEDIDO_NAO_ENCONTRADO),
            "ORDER_NOT_RETURNABLE": (400, "Pedido não está elegível para devolução", PEDIDO_NAO_RETORNAVEL),
            "RETURN_PERIOD_EXPIRED": (400, "Prazo para devolução expirado (7 dias)", DEVOLUCAO_PRAZO_EXPIRADO),
            "RETURN_ALREADY_OPEN": (409, "Já existe uma solicitação aberta para este pedido", DEVOLUCAO_JA_ABERTA),
        }
        if msg in error_map:
            sc, detail, code = error_map[msg]
            _error(sc, detail, code)
        _error(400, msg, msg)
    except PermissionError:
        _error(403, "Pedido não pertence a este consumidor", "PEDIDO_NOT_OWNED")
    return {"id": dev.id, "status": dev.status}


@router.get("/pedidos/{pedido_id}/devolucao", response_model=DevolucaoResponse)
async def consultar_devolucao_endpoint(
    pedido_id: int,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    """Consulta devolução mais recente de um pedido."""
    dev = consultar_devolucao(db, pedido_id=pedido_id, consumidor_id=consumidor.id)
    if not dev:
        _error(404, "Nenhuma devolução encontrada para este pedido", "RETURN_NOT_FOUND")
    motivo_desc = None
    if dev.motivo_id:
        motivo = db.query(MotivoCancelamento).filter(MotivoCancelamento.id == dev.motivo_id).first()
        motivo_desc = motivo.descricao if motivo else None
    return {
        "id": dev.id,
        "status": dev.status,
        "tipo": dev.tipo,
        "motivo_descricao": motivo_desc,
        "descricao": dev.descricao,
        "fotos_json": dev.fotos_json,
        "valor_reembolso": dev.valor_reembolso,
        "resposta_loja": dev.resposta_loja,
        "created_at": dev.created_at,
        "updated_at": dev.updated_at,
    }


@router.get("/motivos-cancelamento", response_model=list[MotivoResponse])
async def listar_motivos_cancelamento(
    db: Session = Depends(get_db),
):
    """Lista motivos de cancelamento ativos."""
    return (
        db.query(MotivoCancelamento)
        .filter(MotivoCancelamento.tipo == "cancelamento", MotivoCancelamento.ativo.is_(True))
        .order_by(MotivoCancelamento.ordem)
        .all()
    )


@router.get("/motivos-devolucao", response_model=list[MotivoResponse])
async def listar_motivos_devolucao(
    db: Session = Depends(get_db),
):
    """Lista motivos de devolução ativos."""
    return (
        db.query(MotivoCancelamento)
        .filter(MotivoCancelamento.tipo == "devolucao", MotivoCancelamento.ativo.is_(True))
        .order_by(MotivoCancelamento.ordem)
        .all()
    )
