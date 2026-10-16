"""Data-access layer. Only place that touches SQLAlchemy."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import CalendarLink, GoogleCredential


class CalendarLinkRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_booking_user(self, booking_id: int, user_id: int) -> CalendarLink | None:
        return self._db.scalar(
            select(CalendarLink).where(
                CalendarLink.booking_id == booking_id,
                CalendarLink.user_id == user_id,
            )
        )

    def list_by_booking(self, booking_id: int) -> list[CalendarLink]:
        return list(
            self._db.scalars(
                select(CalendarLink).where(CalendarLink.booking_id == booking_id)
            )
        )

    def add(self, link: CalendarLink) -> CalendarLink:
        self._db.add(link)
        self._db.flush()
        return link

    def list(self) -> list[CalendarLink]:
        return list(
            self._db.scalars(select(CalendarLink).order_by(CalendarLink.created_at.desc()))
        )

    def count(self) -> int:
        return self._db.scalar(select(func.count()).select_from(CalendarLink)) or 0


class GoogleCredentialRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, user_id: int) -> GoogleCredential | None:
        return self._db.get(GoogleCredential, user_id)

    def upsert(self, cred: GoogleCredential) -> GoogleCredential:
        merged = self._db.merge(cred)
        self._db.flush()
        return merged

    def delete(self, user_id: int) -> bool:
        cred = self._db.get(GoogleCredential, user_id)
        if cred is None:
            return False
        self._db.delete(cred)
        self._db.flush()
        return True
