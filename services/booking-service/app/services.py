"""Application/business layer.

Orchestrates repositories, the Redis lock and Kafka events, and owns the
transaction boundary. Knows nothing about HTTP — it raises domain errors
(see exceptions.py) that the transport layer translates.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from . import events
from .exceptions import (
    BookingNotActive,
    BookingNotFound,
    CannotBookOwnSlot,
    InvalidSlotInterval,
    NotBookingOwner,
    NotSlotParticipant,
    SlotAlreadyBooked,
    SlotBeingBooked,
    SlotNotFound,
)
from .models import Booking, Slot
from .redis_lock import LockNotAcquired, slot_lock
from .repositories import BookingRepository, SlotRepository


class BookingService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._slots = SlotRepository(db)
        self._bookings = BookingRepository(db)

    # ── slots ──────────────────────────────────────────────────
    def create_slot(self, owner_id: int, start_time: datetime, end_time: datetime) -> Slot:
        if end_time <= start_time:
            raise InvalidSlotInterval()
        slot = self._slots.add(
            Slot(owner_id=owner_id, start_time=start_time, end_time=end_time)
        )
        self._db.commit()
        self._db.refresh(slot)
        return slot

    def list_slots(self, owner_id: int | None = None, available_only: bool = True) -> list[dict]:
        slots = self._slots.list(owner_id=owner_id, available_only=available_only)
        result = []
        for slot in slots:
            booking = None
            if slot.status != "available":
                booking = self._bookings.get_active_for_slot(slot.id)
            result.append(self._slot_view(slot, booking))
        return result

    def update_slot_details(
        self,
        slot_id: int,
        user_id: int,
        description: str | None,
        meeting_link: str | None,
    ) -> dict:
        slot = self._slots.get(slot_id)
        if slot is None:
            raise SlotNotFound()
        booking = self._bookings.get_active_for_slot(slot_id)
        is_owner = slot.owner_id == user_id
        is_booker = booking is not None and booking.user_id == user_id
        if not (is_owner or is_booker):
            raise NotSlotParticipant()

        if description is not None:
            slot.description = description
        if meeting_link is not None:
            slot.meeting_link = meeting_link
        self._db.commit()
        self._db.refresh(slot)

        # Re-sync the calendar event only when the slot is actually booked
        # (an event exists for it).
        if booking is not None:
            events.emit_booking_updated(
                booking.id,
                slot.id,
                booking.user_id,
                slot.owner_id,
                slot.start_time,
                slot.end_time,
                slot.description,
                slot.meeting_link,
            )
        return self._slot_view(slot, booking)

    @staticmethod
    def _slot_view(slot: Slot, booking: "Booking | None") -> dict:
        return {
            "id": slot.id,
            "owner_id": slot.owner_id,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "status": slot.status,
            "description": slot.description,
            "meeting_link": slot.meeting_link,
            "booking_id": booking.id if booking else None,
            "booked_by_user_id": booking.user_id if booking else None,
        }

    # ── bookings ───────────────────────────────────────────────
    def book_slot(self, slot_id: int, user_id: int) -> Booking:
        # The Redis lock serialises concurrent attempts on the same slot so the
        # read-check-write below can't race into a double booking.
        try:
            with slot_lock(slot_id):
                slot = self._slots.get(slot_id)
                if slot is None:
                    raise SlotNotFound()
                if slot.owner_id == user_id:
                    raise CannotBookOwnSlot()
                if slot.status != "available":
                    raise SlotAlreadyBooked()

                booking = self._bookings.add(
                    Booking(slot_id=slot_id, user_id=user_id, status="active")
                )
                slot.status = "booked"
                self._db.commit()
                self._db.refresh(booking)
                self._db.refresh(slot)
        except LockNotAcquired:
            raise SlotBeingBooked()

        events.emit_booking_created(
            booking.id,
            slot.id,
            user_id,
            slot.owner_id,
            slot.start_time,
            slot.end_time,
            slot.description,
            slot.meeting_link,
        )
        return booking

    def cancel_booking(self, booking_id: int, user_id: int) -> Booking:
        booking = self._bookings.get(booking_id)
        if booking is None:
            raise BookingNotFound()
        if booking.user_id != user_id:
            raise NotBookingOwner()
        if booking.status != "active":
            raise BookingNotActive()

        booking.status = "cancelled"
        slot = self._slots.get(booking.slot_id)
        if slot is not None:
            slot.status = "available"
        self._db.commit()
        self._db.refresh(booking)

        events.emit_booking_cancelled(
            booking.id,
            booking.slot_id,
            user_id,
            slot.owner_id if slot is not None else None,
            slot.start_time if slot is not None else None,
            slot.end_time if slot is not None else None,
        )
        return booking

    def list_my_bookings(self, user_id: int) -> list[dict]:
        rows = self._bookings.list_for_user_with_slots(user_id)
        return [
            {
                "id": booking.id,
                "slot_id": booking.slot_id,
                "user_id": booking.user_id,
                "status": booking.status,
                "created_at": booking.created_at,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "owner_id": slot.owner_id,
                "description": slot.description,
                "meeting_link": slot.meeting_link,
            }
            for booking, slot in rows
        ]
