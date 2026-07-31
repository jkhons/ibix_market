# PDV Ibix - WebSocket para consumidor mobile (real-time updates)
"""WebSocket com autenticação JWT. Eventos: pedido.status, pagamento.confirmado, mensagem.nova, notificacao.nova."""
import asyncio
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from ...core.auth import AuthConfig
from ...core.brand_module_gating import MODULE_MARKETPLACE, load_brand_module_slugs
from ...database.connection import open_db_session
from ...services.brand_service import normalize_host, resolve_brand_by_host
from ...services.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Loja – WebSocket"])


async def _marketplace_available_for_ws(websocket: WebSocket) -> bool:
    host = normalize_host(websocket.headers.get("host"))

    def _check():
        db = open_db_session(bypass_rls=True)
        try:
            brand = resolve_brand_by_host(db, host)
            slugs = load_brand_module_slugs(db, brand.id)
            return MODULE_MARKETPLACE in slugs
        finally:
            db.close()

    return await asyncio.to_thread(_check)


@router.websocket("/ws/loja/consumidor")
async def websocket_consumidor(
    websocket: WebSocket,
    token: str = Query(...),
):
    if not await _marketplace_available_for_ws(websocket):
        await websocket.close(code=4003, reason="Marketplace indisponível nesta marca")
        return

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
