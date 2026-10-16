"""Domain-level errors for the auth service (mapped to HTTP in main.py)."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status_code: int = 400
    detail: str = "Domain error"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class EmailAlreadyRegistered(DomainError):
    status_code = 409
    detail = "Email already registered"


class InvalidCredentials(DomainError):
    status_code = 401
    detail = "Invalid credentials"


class NotAuthenticated(DomainError):
    status_code = 401
    detail = "Not authenticated"


class InvalidToken(DomainError):
    status_code = 401
    detail = "Invalid or expired token"


class UserNotFound(DomainError):
    status_code = 404
    detail = "User not found"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
