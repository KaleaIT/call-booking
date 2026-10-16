"""Stateless JWT verification.

booking-service does not own users; it only trusts tokens signed by
auth-service. Verification is asymmetric (RS256): we hold the *public* key
only, so we can check a signature but never forge one. We extract the user id
from `sub`.
"""
from functools import lru_cache

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import settings

# auto_error=False so a *missing* Authorization header yields our own 401
# (FastAPI's default would be a 403, inconsistent with the invalid-token case).
bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _public_key() -> str:
    """RSA public key used to verify tokens issued by auth-service."""
    with open(settings.jwt_public_key_path, "r", encoding="utf-8") as fh:
        return fh.read()


def current_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> int:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            creds.credentials, _public_key(), algorithms=[settings.jwt_algorithm]
        )
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
