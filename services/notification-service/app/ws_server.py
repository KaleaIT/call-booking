"""WebSocket server that delivers notifications to connected users in real time.

Subscribes to the Redis pub/sub channel that `consumer.py` publishes to and
fans each notification out to the WebSocket connections of its target user.
On connect it first replays the user's short history (last few notifications),
so the UI is populated even right after a page reload.

Auth is the same stateless RS256 scheme as the other services: we verify the
JWT with the public key only. The browser can't send headers on a WebSocket
handshake, so the token comes in the `?token=` query parameter.
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from functools import lru_cache

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from .config import settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("notification-service.ws")


@lru_cache(maxsize=1)
def _public_key() -> str:
    with open(settings.jwt_public_key_path, "r", encoding="utf-8") as fh:
        return fh.read()


def _user_id_from_token(token: str | None) -> int | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, _public_key(), algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


class ConnectionManager:
    """Tracks live WebSocket connections grouped by user id."""

    def __init__(self) -> None:
        self._conns: dict[int, set[WebSocket]] = {}

    def add(self, user_id: int, ws: WebSocket) -> None:
        self._conns.setdefault(user_id, set()).add(ws)

    def remove(self, user_id: int, ws: WebSocket) -> None:
        conns = self._conns.get(user_id)
        if not conns:
            return
        conns.discard(ws)
        if not conns:
            self._conns.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: str) -> None:
        for ws in list(self._conns.get(user_id, ())):
            try:
                await ws.send_text(message)
            except Exception:  # pragma: no cover - socket already gone
                self.remove(user_id, ws)


manager = ConnectionManager()


async def _pubsub_listener(app: FastAPI) -> None:
    """Forward every published notification to its target user's sockets."""
    r: aioredis.Redis = app.state.redis
    pubsub = r.pubsub()
    await pubsub.subscribe(settings.notifications_channel)
    log.info("subscribed to %s", settings.notifications_channel)
    async for message in pubsub.listen():
        if message.get("type") != "message":
            continue
        try:
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            notification = json.loads(data)
            user_id = int(notification["user_id"])
        except (KeyError, ValueError, json.JSONDecodeError):
            log.warning("dropping malformed notification: %r", message.get("data"))
            continue
        await manager.send_to_user(user_id, data)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(settings.redis_url)
    listener = asyncio.create_task(_pubsub_listener(app))
    try:
        yield
    finally:
        listener.cancel()
        await app.state.redis.aclose()


app = FastAPI(lifespan=lifespan)


@app.get("/notifications/health")
async def health() -> dict:
    return {"status": "ok"}


async def _history(r: aioredis.Redis, user_id: int) -> list[dict]:
    raw = await r.lrange(settings.history_key(user_id), 0, -1)
    items = []
    for entry in raw:
        if isinstance(entry, bytes):
            entry = entry.decode("utf-8")
        try:
            items.append(json.loads(entry))
        except json.JSONDecodeError:
            continue
    return items


@app.websocket("/notifications/ws")
async def notifications_ws(ws: WebSocket) -> None:
    user_id = _user_id_from_token(ws.query_params.get("token"))
    if user_id is None:
        await ws.close(code=1008)  # policy violation: bad/missing token
        return

    await ws.accept()
    history = await _history(ws.app.state.redis, user_id)
    await ws.send_text(json.dumps({"type": "history", "items": history}, default=str))
    manager.add(user_id, ws)
    log.info("user %s connected", user_id)
    try:
        # We don't expect client messages; this just keeps the connection open
        # and lets us notice when the client disconnects.
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.remove(user_id, ws)
        log.info("user %s disconnected", user_id)
