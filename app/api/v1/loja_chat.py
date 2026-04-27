# PDV Ibix - API Chat consumidor ↔ loja (lado consumidor)
"""Conversas e mensagens — requer consumidor autenticado."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...database.connection import get_db
from ...schemas.mobile import (
    ConversaIniciarRequest,
    ConversasListResponse,
    MensagemEnviarRequest,
    MensagemResponse,
)
from ...services.chat_marketplace_service import (
    enviar_mensagem_consumidor,
    iniciar_conversa,
    listar_conversas_consumidor,
    listar_mensagens,
    marcar_lida_consumidor,
)
from .loja import get_current_consumidor

router = APIRouter(prefix="/loja/conversas", tags=["Loja – Chat"])


@router.get("", response_model=ConversasListResponse)
async def listar_minhas_conversas(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    items, total = listar_conversas_consumidor(db, consumidor.id, offset=offset, limit=limit)
    return {"items": items, "total": total}


@router.post("", status_code=201)
async def iniciar_conversa_endpoint(
    body: ConversaIniciarRequest,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    try:
        conversa, msg = iniciar_conversa(
            db,
            consumidor_id=consumidor.id,
            loja_id=body.loja_id,
            mensagem_texto=body.mensagem,
            anuncio_id=body.anuncio_id,
        )
    except ValueError as e:
        msg_str = str(e)
        if msg_str == "LOJA_NOT_FOUND":
            raise HTTPException(status_code=404, detail={"detail": "Loja não encontrada", "code": "LOJA_NOT_FOUND"})
        raise HTTPException(status_code=400, detail={"detail": msg_str, "code": msg_str})
    return {"conversa_id": conversa.id, "mensagem_id": msg.id}


@router.get("/{conversa_id}/mensagens", response_model=list[MensagemResponse])
async def listar_mensagens_endpoint(
    conversa_id: int,
    before_id: int = Query(None),
    limit: int = Query(30, ge=1, le=100),
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    try:
        msgs = listar_mensagens(db, conversa_id, consumidor.id, before_id=before_id, limit=limit)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Conversa não pertence a este consumidor")
    return msgs


@router.post("/{conversa_id}/mensagens", response_model=MensagemResponse, status_code=201)
async def enviar_mensagem_endpoint(
    conversa_id: int,
    body: MensagemEnviarRequest,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    try:
        msg = enviar_mensagem_consumidor(
            db, conversa_id, consumidor.id,
            texto=body.texto, imagem_url=body.imagem_url,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Conversa não pertence a este consumidor")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return msg


@router.patch("/{conversa_id}/lida")
async def marcar_conversa_lida(
    conversa_id: int,
    consumidor=Depends(get_current_consumidor),
    db: Session = Depends(get_db),
):
    try:
        count = marcar_lida_consumidor(db, conversa_id, consumidor.id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Conversa não pertence a este consumidor")
    return {"marcadas": count}
