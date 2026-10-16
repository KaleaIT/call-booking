"""Stateless JWT verification.

calendar-service does not own users; the OAuth endpoints only need to know
*which* user is connecting their Google account. We trust tokens signed by
auth-service and verify them asymmetrically (RS256) with the public key only.
"""
from functools import lru_cache

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import settings

bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _public_key() -> str:
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
