# PDV Ibix - WebSocket para consumidor mobile (real-time updates)
"""WebSocket com autenticação JWT. Eventos: pedido.status, pagamento.confirmado, mensagem.nova, notificacao.nova."""
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from ...core.auth import AuthConfig
from ...services.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Loja – WebSocket"])


@router.websocket("/ws/loja/consumidor")
async def websocket_consumidor(
    websocket: WebSocket,
    token: str = Query(...),
):
    try:
        payload = AuthConfig.verify_token(token)
    except (JWTError, ValueError, KeyError):
        await websocket.close(code=4001, reason="Token inválido")
        return

    if payload.get("tipo") != "consumidor":
        await websocket.close(code=4001, reason="Token inválido para consumidor")
        return

    try:
        consumidor_id = int(payload.get("sub", 0))
    except (TypeError, ValueError):
        await websocket.close(code=4001, reason="Token inválido")
        return

    await manager.connect(consumidor_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("WebSocket erro inesperado para consumidor %s", consumidor_id)
    finally:
        manager.disconnect(consumidor_id, websocket)
