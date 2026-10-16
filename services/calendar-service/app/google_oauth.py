"""Google OAuth 2.0 flow + credential persistence.

Responsibilities:
  * build the consent-screen URL (offline access -> we get a refresh token),
  * exchange the authorization code for tokens and capture the Google email,
  * persist/refresh per-user credentials and hand back a ready-to-use
    `google.oauth2.credentials.Credentials` for the Calendar API,
  * sign/verify the OAuth `state` so the callback knows which user it is for.
"""
import logging
import os

import httpx
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings
from .models import GoogleCredential
from .repositories import GoogleCredentialRepository

# The redirect URI is plain http in local dev, and Google may append the
# `openid` scope to what we asked for — relax oauthlib so neither raises.
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

log = logging.getLogger("calendar-service.google_oauth")

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]
TOKEN_URI = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": TOKEN_URI,
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def _flow() -> Flow:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = settings.google_redirect_uri
    return flow


# ── state signing (HS256 with the client secret as the key) ─────────────
def encode_state(user_id: int) -> str:
    return jwt.encode({"uid": user_id}, settings.google_client_secret, algorithm="HS256")


def decode_state(state: str) -> int | None:
    try:
        data = jwt.decode(state, settings.google_client_secret, algorithms=["HS256"])
        return int(data["uid"])
    except (JWTError, KeyError, ValueError):
        return None


# ── consent + token exchange ────────────────────────────────────────────
def build_authorization_url(state: str) -> str:
    url, _ = _flow().authorization_url(
        access_type="offline",          # ask for a refresh token
        include_granted_scopes="true",
        prompt="consent",               # force a refresh token on re-connect
        state=state,
    )
    return url


def exchange_code(code: str) -> tuple[Credentials, str | None]:
    flow = _flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    return creds, _fetch_email(creds.token)


def _fetch_email(access_token: str) -> str | None:
    try:
        resp = httpx.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5.0,
        )
        if resp.status_code == 200:
            return resp.json().get("email")
    except httpx.HTTPError as exc:  # pragma: no cover
        log.warning("failed to fetch google userinfo: %s", exc)
    return None


# ── persistence ─────────────────────────────────────────────────────────
def save_credentials(db: Session, user_id: int, creds: Credentials, email: str | None) -> None:
    repo = GoogleCredentialRepository(db)
    existing = repo.get(user_id)
    # Google only returns a refresh token on the first consent; keep the old one
    # if this exchange didn't include one.
    refresh_token = creds.refresh_token or (existing.refresh_token if existing else None)
    repo.upsert(
        GoogleCredential(
            user_id=user_id,
            refresh_token=refresh_token,
            access_token=creds.token,
            token_expiry=creds.expiry,
            google_email=email or (existing.google_email if existing else None),
            scopes=" ".join(creds.scopes or SCOPES),
        )
    )
    db.commit()


def load_credentials(db: Session, user_id: int | None) -> Credentials | None:
    """Return usable Credentials for a user, refreshing + persisting the access
    token if it has expired. None if the user hasn't connected Google."""
    if user_id is None:
        return None
    repo = GoogleCredentialRepository(db)
    row = repo.get(user_id)
    if row is None or not row.refresh_token:
        return None

    creds = Credentials(
        token=row.access_token,
        refresh_token=row.refresh_token,
        token_uri=TOKEN_URI,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=(row.scopes or "").split() or SCOPES,
    )
    if not creds.valid:
        try:
            creds.refresh(GoogleRequest())
            row.access_token = creds.token
            row.token_expiry = creds.expiry
            db.commit()
        except Exception:  # pragma: no cover - refresh failure (revoked, etc.)
            log.exception("failed to refresh google token for user %s", user_id)
            return None
    return creds


def get_status(db: Session, user_id: int) -> dict:
    row = GoogleCredentialRepository(db).get(user_id)
    connected = bool(row and row.refresh_token)
    return {"connected": connected, "google_email": row.google_email if row else None}


def disconnect(db: Session, user_id: int) -> bool:
    removed = GoogleCredentialRepository(db).delete(user_id)
    db.commit()
    return removed
