# PDV Ibix - WebSocket connection manager com Redis pub/sub
"""Gerencia conexões WebSocket por consumidor_id. Em multi-worker, Redis pub/sub garante entrega."""
import asyncio
import json
import logging
from typing import Any, Dict, Set

from starlette.websockets import WebSocket, WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._redis_tasks: Dict[int, asyncio.Task] = {}

    async def connect(self, consumidor_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        if consumidor_id not in self._connections:
            self._connections[consumidor_id] = set()
        self._connections[consumidor_id].add(websocket)

        if consumidor_id not in self._redis_tasks:
            self._redis_tasks[consumidor_id] = asyncio.create_task(
                self._redis_listener(consumidor_id)
            )

    def disconnect(self, consumidor_id: int, websocket: WebSocket) -> None:
        if consumidor_id in self._connections:
            self._connections[consumidor_id].discard(websocket)
            if not self._connections[consumidor_id]:
                del self._connections[consumidor_id]
                task = self._redis_tasks.pop(consumidor_id, None)
                if task:
                    task.cancel()

    async def send_to_consumidor(self, consumidor_id: int, event_type: str, data: Any) -> None:
        payload = json.dumps({"type": event_type, "data": data})
        conns = self._connections.get(consumidor_id, set()).copy()
        for ws in conns:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
            except Exception:
                self.disconnect(consumidor_id, ws)

    async def _redis_listener(self, consumidor_id: int) -> None:
        pubsub = None
        try:
            from app.core.redis_client import get_redis_client
            r = get_redis_client()
            if not r:
                return
            pubsub = r.pubsub()
            channel = f"mobile:consumidor:{consumidor_id}"
            pubsub.subscribe(channel)

            while consumidor_id in self._connections:
                msg = await asyncio.to_thread(
                    pubsub.get_message, ignore_subscribe_messages=True, timeout=1.0
                )
                if msg and msg["type"] == "message":
                    data = msg["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    try:
                        parsed = json.loads(data)
                        await self.send_to_consumidor(
                            consumidor_id,
                            parsed.get("type", "event"),
                            parsed.get("data"),
                        )
                    except json.JSONDecodeError:
                        logger.warning("WS Redis: JSON inválido no canal %s", channel)
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except ImportError:
            logger.error("WS Redis: redis_client não disponível")
        except Exception:
            logger.exception("WS Redis listener erro para consumidor %s", consumidor_id)
        finally:
            if pubsub:
                try:
                    pubsub.unsubscribe()
                    pubsub.close()
                except Exception:
                    pass


manager = ConnectionManager()


def publish_event(consumidor_id: int, event_type: str, data: Any) -> None:
    """Publica evento via Redis para que todos os workers entreguem ao consumidor via WebSocket."""
    try:
        from app.core.redis_client import get_redis_client
        r = get_redis_client()
        if not r:
            return
        payload = json.dumps({"type": event_type, "data": data})
        r.publish(f"mobile:consumidor:{consumidor_id}", payload)
    except Exception:
        logger.exception("WS publish_event falhou para consumidor %s", consumidor_id)
