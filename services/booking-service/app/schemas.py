from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class SlotUpdate(BaseModel):
    # Meeting details a participant fills in for a booked slot. Both optional —
    # the client may send either field on its own.
    description: str | None = None
    meeting_link: str | None = None


class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    start_time: datetime
    end_time: datetime
    status: str
    description: str | None = None
    meeting_link: str | None = None
    # Present only for booked slots, so the host sees who reserved the slot.
    booking_id: int | None = None
    booked_by_user_id: int | None = None


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slot_id: int
    user_id: int
    status: str
    created_at: datetime
    # Denormalised slot details so the dashboard can render "with whom / when /
    # where" without extra round-trips. Null on the bare action responses
    # (book/cancel) that return the ORM Booking directly.
    start_time: datetime | None = None
    end_time: datetime | None = None
    owner_id: int | None = None
    description: str | None = None
    meeting_link: str | None = None
