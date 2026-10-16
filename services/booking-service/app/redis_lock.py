"""Redis-based distributed lock to prevent double-booking.

A booking attempt must hold `lock:slot:<id>` before it reads+updates the
slot. Two concurrent requests for the same slot serialise here, so only one
can observe the slot as `available` and book it.
"""
import contextlib
import uuid

import redis

from .config import settings


class LockNotAcquired(Exception):
    """Raised when the slot lock is already held by another request."""

_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_lock_db,
    decode_responses=True,
)

# Release only if we still own the lock (atomic compare-and-delete).
_RELEASE = _client.register_script(
    """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
)


def ping() -> bool:
    return bool(_client.ping())


@contextlib.contextmanager
def slot_lock(slot_id: int, ttl_ms: int = 5000):
    key = f"lock:slot:{slot_id}"
    token = uuid.uuid4().hex
    acquired = _client.set(key, token, nx=True, px=ttl_ms)
    if not acquired:
        raise LockNotAcquired(f"slot {slot_id} is locked by another request")
    try:
        yield
    finally:
        _RELEASE(keys=[key], args=[token])
