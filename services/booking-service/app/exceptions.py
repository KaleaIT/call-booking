"""Domain-level errors for the booking service.

The service/repository layers raise these; a single FastAPI exception handler
(registered in main.py) maps them to HTTP responses. This keeps endpoints and
business logic free of transport concerns.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base class. Subclasses set an HTTP status_code and default detail."""

    status_code: int = 400
    detail: str = "Domain error"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class InvalidSlotInterval(DomainError):
    status_code = 422
    detail = "end_time must be after start_time"


class SlotNotFound(DomainError):
    status_code = 404
    detail = "Slot not found"


class SlotAlreadyBooked(DomainError):
    status_code = 409
    detail = "Slot already booked"


class CannotBookOwnSlot(DomainError):
    status_code = 400
    detail = "You cannot book your own slot"


class SlotBeingBooked(DomainError):
    status_code = 409
    detail = "Slot is being booked, try again"


class BookingNotFound(DomainError):
    status_code = 404
    detail = "Booking not found"


class NotBookingOwner(DomainError):
    status_code = 403
    detail = "Not your booking"


class BookingNotActive(DomainError):
    status_code = 409
    detail = "Booking is not active"


class NotSlotParticipant(DomainError):
    status_code = 403
    detail = "Only the host or the person who booked can edit this slot"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
