"""Calendar business logic.

Reacts to booking events and keeps each participant's Google Calendar in sync:

  booking.created / booking.updated -> upsert an event in every connected
                                        participant's calendar (the other party
                                        is added as an attendee).
  booking.cancelled                 -> delete those events.

A participant who hasn't connected Google is simply skipped — the booking still
lives in their dashboard, just not in Google. Owns the transaction boundary.
"""
import logging

from sqlalchemy.orm import Session

from . import auth_client, google_calendar, google_oauth
from .models import CalendarLink
from .repositories import CalendarLinkRepository

log = logging.getLogger("calendar-service.service")


class CalendarService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._links = CalendarLinkRepository(db)

    # ── event handlers ─────────────────────────────────────────────
    def on_booking_created(
        self,
        booking_id: int,
        owner_id: int | None,
        user_id: int | None,
        start_time=None,
        end_time=None,
        description=None,
        meeting_link=None,
    ) -> None:
        self._sync(
            booking_id, owner_id, user_id, start_time, end_time, description, meeting_link
        )

    def on_booking_updated(
        self,
        booking_id: int,
        owner_id: int | None,
        user_id: int | None,
        start_time=None,
        end_time=None,
        description=None,
        meeting_link=None,
    ) -> None:
        # Same idempotent path: existing events get patched, and a participant
        # who connected Google *after* booking gets their event created now.
        self._sync(
            booking_id, owner_id, user_id, start_time, end_time, description, meeting_link
        )

    def on_booking_cancelled(self, booking_id: int) -> None:
        links = self._links.list_by_booking(booking_id)
        if not links:
            log.info("no calendar links for cancelled booking %s", booking_id)
            return
        for link in links:
            if link.status != "active":
                continue
            creds = google_oauth.load_credentials(self._db, link.user_id)
            if creds is not None:
                try:
                    google_calendar.delete_event(creds, link.external_event_id)
                except Exception:  # pragma: no cover - keep cancelling others
                    log.exception(
                        "failed to delete event %s for user %s",
                        link.external_event_id,
                        link.user_id,
                    )
            link.status = "cancelled"
            self._db.commit()
        log.info("cancelled calendar events for booking %s", booking_id)

    # ── core sync ──────────────────────────────────────────────────
    def _sync(
        self,
        booking_id: int,
        owner_id: int | None,
        user_id: int | None,
        start_time,
        end_time,
        description,
        meeting_link,
    ) -> None:
        participants = self._participants(owner_id, user_id)
        attendee_emails = [p["email"] for p in participants.values() if p.get("email")]

        for uid in (owner_id, user_id):
            if uid is None:
                continue
            creds = google_oauth.load_credentials(self._db, uid)
            if creds is None:
                log.info("user %s has no Google connection; skipping event", uid)
                continue

            other_id = owner_id if uid == user_id else user_id
            other_name = (participants.get(other_id) or {}).get("full_name") or "участник"
            summary = f"Созвон с {other_name}"
            link = self._links.get_by_booking_user(booking_id, uid)

            try:
                if link is None:
                    event_id = google_calendar.create_event(
                        creds, summary, description, meeting_link,
                        start_time, end_time, attendee_emails,
                    )
                    self._links.add(
                        CalendarLink(
                            booking_id=booking_id,
                            user_id=uid,
                            external_event_id=event_id,
                            calendar_id="primary",
                            status="active",
                        )
                    )
                    log.info("linked booking %s for user %s -> %s", booking_id, uid, event_id)
                elif link.status == "active":
                    google_calendar.update_event(
                        creds, link.external_event_id, summary, description,
                        meeting_link, start_time, end_time,
                    )
                self._db.commit()
            except Exception:  # pragma: no cover - don't let one user block the other
                log.exception("failed to sync event for booking %s user %s", booking_id, uid)
                self._db.rollback()

    def _participants(self, *user_ids: int | None) -> dict:
        result: dict[int, dict] = {}
        for uid in {u for u in user_ids if u is not None}:
            info = auth_client.get_user(uid)
            if info:
                result[uid] = info
        return result

    # ── read model (debug) ─────────────────────────────────────────
    def list_links(self) -> dict:
        links = self._links.list()
        return {
            "total": self._links.count(),
            "links": [
                {
                    "booking_id": l.booking_id,
                    "user_id": l.user_id,
                    "external_event_id": l.external_event_id,
                    "status": l.status,
                }
                for l in links
            ],
        }
