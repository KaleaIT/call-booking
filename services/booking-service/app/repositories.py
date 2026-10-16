"""Data-access layer.

Repositories are the ONLY place that knows about SQLAlchemy / the schema.
They stage changes (add/flush) and run queries, but do NOT manage transaction
boundaries — committing is the service layer's responsibility (unit of work).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Booking, Slot


class SlotRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, slot_id: int) -> Slot | None:
        return self._db.get(Slot, slot_id)

    def add(self, slot: Slot) -> Slot:
        self._db.add(slot)
        self._db.flush()  # assign PK without committing
        return slot

    def list(self, owner_id: int | None = None, available_only: bool = True) -> list[Slot]:
        stmt = select(Slot).order_by(Slot.start_time)
        if owner_id is not None:
            stmt = stmt.where(Slot.owner_id == owner_id)
        if available_only:
            stmt = stmt.where(Slot.status == "available")
        return list(self._db.scalars(stmt))


class BookingRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, booking_id: int) -> Booking | None:
        return self._db.get(Booking, booking_id)

    def add(self, booking: Booking) -> Booking:
        self._db.add(booking)
        self._db.flush()
        return booking

    def list_for_user(self, user_id: int) -> list[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.user_id == user_id)
            .order_by(Booking.created_at.desc())
        )
        return list(self._db.scalars(stmt))

    def list_for_user_with_slots(self, user_id: int) -> list[tuple[Booking, Slot]]:
        """Bookings of a user joined with their slot, so the read model can show
        when/with-whom/where without a second query per row."""
        stmt = (
            select(Booking, Slot)
            .join(Slot, Booking.slot_id == Slot.id)
            .where(Booking.user_id == user_id)
            .order_by(Booking.created_at.desc())
        )
        return [tuple(row) for row in self._db.execute(stmt).all()]

    def get_active_for_slot(self, slot_id: int) -> Booking | None:
        stmt = select(Booking).where(
            Booking.slot_id == slot_id, Booking.status == "active"
        )
        return self._db.scalar(stmt)
