"""FastAPI dependency wiring for the auth service."""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .exceptions import NotAuthenticated
from .models import User
from .services import AuthService

# auto_error=False -> missing header returns our own 401 (not FastAPI's 403).
_bearer = HTTPBearer(auto_error=False)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    svc: AuthService = Depends(get_auth_service),
) -> User:
    if creds is None:
        raise NotAuthenticated()
    return svc.user_from_token(creds.credentials)
