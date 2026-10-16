"""Transport layer: HTTP endpoints only — delegate to AuthService."""
import logging

from fastapi import Depends, FastAPI, status

from .dependencies import current_user, get_auth_service
from .exceptions import register_exception_handlers
from .models import User
from .schemas import (
    LoginRequest,
    PublicUserResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from .services import AuthService

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("auth-service")

# docs/openapi under the /auth prefix so they work through the gateway
# (which preserves the path) at /auth/docs, and directly too.
app = FastAPI(
    title="auth-service",
    version="1.0.0",
    docs_url="/auth/docs",
    redoc_url="/auth/redoc",
    openapi_url="/auth/openapi.json",
)
register_exception_handlers(app)


@app.on_event("startup")
def on_startup() -> None:
    # Schema is managed by Alembic (applied by entrypoint.sh before launch),
    # not create_all — see migrations/.
    log.info("auth-service started")


@app.get("/health")
@app.get("/auth/health")
def health() -> dict:
    # /health for direct port + Docker healthcheck; /auth/health via gateway.
    return {"status": "ok", "service": "auth-service"}


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    svc: AuthService = Depends(get_auth_service),
) -> User:
    return svc.register(payload.email, payload.password, payload.full_name)


@app.post("/auth/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    svc: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return TokenResponse(access_token=svc.login(payload.email, payload.password))


@app.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(current_user)) -> User:
    return user


@app.get("/auth/users/{user_id}", response_model=PublicUserResponse)
def public_user(
    user_id: int,
    svc: AuthService = Depends(get_auth_service),
) -> User:
    # Public: lets a booking page show whose calendar it is.
    return svc.get_public_user(user_id)
