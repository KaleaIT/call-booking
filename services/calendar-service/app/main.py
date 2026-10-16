import logging
import threading

from fastapi import Depends, FastAPI, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from . import google_oauth
from .auth import current_user_id
from .consumer import run_consumer
from .database import get_db
from .services import CalendarService

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("calendar-service")

app = FastAPI(
    title="calendar-service",
    version="1.0.0",
    docs_url="/calendar/docs",
    redoc_url="/calendar/redoc",
    openapi_url="/calendar/openapi.json",
)


@app.on_event("startup")
def on_startup() -> None:
    # Schema is managed by Alembic (applied by entrypoint.sh before launch),
    # not create_all — see migrations/.
    # Consumer runs in a daemon thread alongside the healthcheck API.
    thread = threading.Thread(target=run_consumer, daemon=True, name="kafka-consumer")
    thread.start()
    log.info("calendar-service started, consumer thread launched")


@app.get("/health")
@app.get("/calendar/health")
def health() -> dict:
    return {"status": "ok", "service": "calendar-service"}


@app.get("/calendar/links")
def list_links(db: Session = Depends(get_db)) -> dict:
    """Inspect the booking -> external event mapping (for debugging)."""
    return CalendarService(db).list_links()


# ──────────────────────── Google OAuth ────────────────────────
@app.get("/calendar/google/status")
def google_status(
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    return google_oauth.get_status(db, user_id)


@app.get("/calendar/google/authorize")
def google_authorize(user_id: int = Depends(current_user_id)) -> dict:
    # `state` is signed with the user id so the (auth-less) callback knows who
    # is connecting after the Google round-trip.
    state = google_oauth.encode_state(user_id)
    return {"url": google_oauth.build_authorization_url(state)}


@app.get("/calendar/google/callback", response_class=HTMLResponse)
def google_callback(
    state: str = Query(...),
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    # Google redirects the browser here (no Authorization header), so we trust
    # the signed state instead.
    user_id = google_oauth.decode_state(state)
    status = "error"
    if error:
        log.warning("google oauth declined: %s", error)
    elif user_id is None:
        log.warning("google oauth callback with invalid state")
    elif code:
        try:
            creds, email = google_oauth.exchange_code(code)
            google_oauth.save_credentials(db, user_id, creds, email)
            status = "connected"
            log.info("stored google credentials for user %s (%s)", user_id, email)
        except Exception:  # pragma: no cover - surface failure to the popup
            log.exception("failed to complete google oauth for user %s", user_id)
    return HTMLResponse(_callback_html(status))


@app.post("/calendar/google/disconnect")
def google_disconnect(
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    google_oauth.disconnect(db, user_id)
    return {"status": "disconnected"}


def _callback_html(status: str) -> str:
    message = (
        "Google Calendar подключён. Можно закрыть это окно."
        if status == "connected"
        else "Не удалось подключить Google Calendar. Закройте окно и попробуйте снова."
    )
    return (
        "<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\">"
        "<title>Google Calendar</title></head>"
        "<body style=\"font-family:system-ui;padding:40px;text-align:center\">"
        f"<p>{message}</p>"
        "<script>(function(){try{if(window.opener){window.opener.postMessage("
        f"{{source:'google-oauth',status:'{status}'}},'*');}}}}catch(e){{}}"
        "setTimeout(function(){window.close();},900);})();</script>"
        "</body></html>"
    )
