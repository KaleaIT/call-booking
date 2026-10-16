"""Tiny read-only client for auth-service.

The calendar event needs participants' email (attendees) and name (event title).
auth-service owns users, so we resolve them over HTTP via its public endpoint.
Failures are non-fatal — we degrade to whatever info we have.
"""
import logging

import httpx

from .config import settings

log = logging.getLogger("calendar-service.auth_client")


def get_user(user_id: int | None) -> dict | None:
    if user_id is None:
        return None
    url = f"{settings.auth_service_url}/auth/users/{user_id}"
    try:
        resp = httpx.get(url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            return {"email": data.get("email"), "full_name": data.get("full_name")}
        log.warning("auth-service returned %s for user %s", resp.status_code, user_id)
    except httpx.HTTPError as exc:  # pragma: no cover - network failure path
        log.warning("failed to fetch user %s: %s", user_id, exc)
    return None
