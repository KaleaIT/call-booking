from datetime import datetime, timedelta, timezone
from functools import lru_cache

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@lru_cache(maxsize=1)
def _private_key() -> str:
    """RSA private key used to sign tokens (read once, cached)."""
    with open(settings.jwt_private_key_path, "r", encoding="utf-8") as fh:
        return fh.read()


@lru_cache(maxsize=1)
def _public_key() -> str:
    """RSA public key used to verify our own tokens (e.g. /auth/me)."""
    with open(settings.jwt_public_key_path, "r", encoding="utf-8") as fh:
        return fh.read()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _private_key(), algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _public_key(), algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
