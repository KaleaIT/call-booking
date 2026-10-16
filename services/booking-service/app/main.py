"""Transport layer: HTTP endpoints only.

No DB access, no business logic here — every handler just delegates to
BookingService and returns the result. Domain errors are translated to HTTP
by the handler registered in exceptions.register_exception_handlers.
"""
import logging

from fastapi import Depends, FastAPI

from .auth import current_user_id
from .dependencies import get_booking_service
from .exceptions import register_exception_handlers
from .redis_lock import ping as redis_ping
from .schemas import BookingResponse, SlotCreate, SlotResponse, SlotUpdate
from .services import BookingService

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("booking-service")

app = FastAPI(
    title="booking-service",
    version="1.0.0",
    docs_url="/booking/docs",
    redoc_url="/booking/redoc",
    openapi_url="/booking/openapi.json",
)
register_exception_handlers(app)


@app.on_event("startup")
def on_startup() -> None:
    # Schema is managed by Alembic (applied by entrypoint.sh before launch),
    # not create_all — see migrations/.
    log.info("booking-service started")


@app.get("/health")
@app.get("/booking/health")
def health() -> dict:
    try:
        redis_ok = redis_ping()
    except Exception:  # pragma: no cover
        redis_ok = False
    return {"status": "ok", "service": "booking-service", "redis": redis_ok}


# ──────────────────────────── Slots ────────────────────────────
@app.post("/booking/slots", response_model=SlotResponse, status_code=201)
def create_slot(
    payload: SlotCreate,
    svc: BookingService = Depends(get_booking_service),
    user_id: int = Depends(current_user_id),
) -> SlotResponse:
    return svc.create_slot(user_id, payload.start_time, payload.end_time)


@app.get("/booking/slots", response_model=list[SlotResponse])
def list_slots(
    owner_id: int | None = None,
    available_only: bool = True,
    svc: BookingService = Depends(get_booking_service),
) -> list[SlotResponse]:
    # Public: a visitor can browse a host's availability without logging in
    # (Calendly-style). Booking still requires auth.
    return svc.list_slots(owner_id=owner_id, available_only=available_only)


@app.patch("/booking/slots/{slot_id}", response_model=SlotResponse)
def update_slot(
    slot_id: int,
    payload: SlotUpdate,
    svc: BookingService = Depends(get_booking_service),
    user_id: int = Depends(current_user_id),
) -> SlotResponse:
    # Either participant of a booked slot can set the meeting description/link;
    # the change is re-synced to the calendar via booking.updated.
    return svc.update_slot_details(
        slot_id, user_id, payload.description, payload.meeting_link
    )


# ─────────────────────────── Bookings ──────────────────────────
@app.post("/booking/slots/{slot_id}/book", response_model=BookingResponse, status_code=201)
def book_slot(
    slot_id: int,
    svc: BookingService = Depends(get_booking_service),
    user_id: int = Depends(current_user_id),
) -> BookingResponse:
    return svc.book_slot(slot_id, user_id)


@app.post("/booking/bookings/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    svc: BookingService = Depends(get_booking_service),
    user_id: int = Depends(current_user_id),
) -> BookingResponse:
    return svc.cancel_booking(booking_id, user_id)


@app.get("/booking/bookings/mine", response_model=list[BookingResponse])
def my_bookings(
    svc: BookingService = Depends(get_booking_service),
    user_id: int = Depends(current_user_id),
) -> list[BookingResponse]:
    return svc.list_my_bookings(user_id)
