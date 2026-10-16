"""FastAPI dependency wiring: build a BookingService bound to a request DB session."""
from fastapi import Depends
from sqlalchemy.orm import Session

from .database import get_db
from .services import BookingService


def get_booking_service(db: Session = Depends(get_db)) -> BookingService:
    return BookingService(db)
