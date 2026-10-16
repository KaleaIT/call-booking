from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CalendarLink(Base):
    """Maps an internal booking to a Google Calendar event in ONE participant's
    calendar. A booking can have up to two links (host + guest), so the unique
    key is (booking_id, user_id) rather than booking_id alone."""

    __tablename__ = "calendar_links"
    __table_args__ = (
        UniqueConstraint("booking_id", "user_id", name="uq_calendar_links_booking_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    # Whose calendar this event lives in.
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(256), nullable=False)
    calendar_id: Mapped[str] = mapped_column(String(256), default="primary", nullable=False)
    # active | cancelled
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GoogleCredential(Base):
    """A user's stored Google OAuth tokens. Keyed by the platform user id so the
    consumer can act on a user's calendar on their behalf (offline access)."""

    __tablename__ = "google_credentials"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    google_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
