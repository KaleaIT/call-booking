"""Real Google Calendar integration.

Thin wrapper over the Calendar v3 API. Each function takes a per-user
`Credentials` and acts on that user's primary calendar.
"""
import logging
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

log = logging.getLogger("calendar-service.google")

CALENDAR_ID = "primary"


def _service(creds: Credentials):
    # cache_discovery=False avoids a noisy warning and file-cache writes.
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _to_rfc3339(value) -> str:
    """Kafka delivers timestamps as strings (json default=str -> e.g.
    '2026-06-13 14:00:00+00:00'). Normalise to RFC3339 ('T' separator) which
    the Calendar API requires. Naive values are assumed UTC."""
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _event_body(summary, description, location, start_time, end_time, attendees=None) -> dict:
    body = {
        "summary": summary,
        "description": description or "",
        "location": location or "",
        "start": {"dateTime": _to_rfc3339(start_time)},
        "end": {"dateTime": _to_rfc3339(end_time)},
    }
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees if e]
    return body


def create_event(
    creds: Credentials,
    summary: str,
    description: str,
    location: str,
    start_time,
    end_time,
    attendees=None,
) -> str:
    body = _event_body(summary, description, location, start_time, end_time, attendees)
    event = (
        _service(creds)
        .events()
        .insert(calendarId=CALENDAR_ID, body=body, sendUpdates="all")
        .execute()
    )
    log.info("created google event %s", event.get("id"))
    return event["id"]


def update_event(
    creds: Credentials,
    event_id: str,
    summary: str,
    description: str,
    location: str,
    start_time,
    end_time,
) -> None:
    body = _event_body(summary, description, location, start_time, end_time)
    _service(creds).events().patch(
        calendarId=CALENDAR_ID, eventId=event_id, body=body, sendUpdates="all"
    ).execute()
    log.info("updated google event %s", event_id)


def delete_event(creds: Credentials, event_id: str) -> None:
    try:
        _service(creds).events().delete(
            calendarId=CALENDAR_ID, eventId=event_id, sendUpdates="all"
        ).execute()
        log.info("deleted google event %s", event_id)
    except HttpError as exc:
        # Already gone — treat as success (idempotent cancel).
        if exc.resp is not None and exc.resp.status in (404, 410):
            log.info("google event %s already absent", event_id)
            return
        raise
