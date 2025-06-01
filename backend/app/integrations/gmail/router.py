"""
Routes for Gmail OAuth 2.0  +  listing cached Gmail threads
────────────────────────────────────────────────────────────
Table layout assumptions
------------------------
DynamoDB triagely-oauth     PK=UserID,  SK='gmail',   attrs: tokens + client-id
DynamoDB triagely-messages  PK=UserID,  SK=MessageID, attrs: cached thread data
"""

from __future__ import annotations

import json
import os
from email.utils import parsedate_to_datetime
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow

from app.core.auth    import current_user
from app.core.db      import list_msgs, save_token
from app.core.secrets import get as get_secret
from .schemas         import GmailMessage

router = APIRouter(prefix="/gmail", tags=["gmail"])

# ────────────────────────────────────────────────────────────
# Config helpers
# ────────────────────────────────────────────────────────────
SECRET = get_secret("gmail-oauth")  # { client_id, client_secret }

SCOPES = (
    os.getenv(
        "GMAIL_SCOPES",
        "https://www.googleapis.com/auth/gmail.readonly",
    ).split(",")
)


def _detect_redirect() -> str:
    """
    Single source of truth for the redirect URI.

    precedence:
        1. env var `GMAIL_REDIRECT_URL`
        2. env vars `API_HOST` + `API_PORT`  (handy for Docker)
        3. sane localhost default
    """
    env_uri = os.getenv("GMAIL_REDIRECT_URL")
    if env_uri:
        return env_uri.rstrip("/")

    host = os.getenv("API_HOST", "localhost")
    port = int(os.getenv("API_PORT", "8000"))
    return f"http://{host}:{port}/gmail/callback"


REDIRECT_URI = _detect_redirect()


def _flow(state: str | None):
    """Return an OAuth Flow instance in the required config shape."""
    return Flow.from_client_config(
        {
            "web": {
                "client_id": SECRET["client_id"],
                "client_secret": SECRET["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state=state,
    )


def _hdrs_to_dict(payload_headers: list[dict]) -> dict[str, str]:
    """Gmail returns headers as list-of-dicts; flatten & lower-case names."""
    return {h["name"].lower(): h["value"] for h in payload_headers}


# ────────────────────────────────────────────────────────────
# OAuth 2.0 endpoints
# ────────────────────────────────────────────────────────────
@router.get("/connect")
async def connect(user=Depends(current_user)):
    """Return the Google consent URL for the current user."""
    auth_url, _ = _flow(user["sub"]).authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    return {"auth_url": auth_url}


@router.get("/callback")
async def callback(request: Request, state: str = "", code: str = ""):
    flow = _flow(state)
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise HTTPException(400, f"Token exchange failed: {exc}")

    creds = flow.credentials
    save_token(
        state,  # Cognito sub == UserID
        "gmail",
        {
            "refresh_token": creds.refresh_token,
            "access_token":  creds.token,
            "expires_at":    int(creds.expiry.timestamp()),
            "token_uri":     creds.token_uri,
            "client_id":     SECRET["client_id"],
            "client_secret": SECRET["client_secret"],
            "scopes":        creds.scopes,
        },
    )
    # 👇👇👇 Redirect to the SPA
    return RedirectResponse("http://localhost:3000/connected?provider=gmail")



# ────────────────────────────────────────────────────────────
# List cached messages for the SPA
# ────────────────────────────────────────────────────────────
@router.get("/messages", response_model=List[GmailMessage])
async def list_messages(limit: int = 50, user=Depends(current_user)):
    """Return the most recent cached Gmail threads for the signed-in user."""
    raw = list_msgs(user["sub"], limit)

    out: list[GmailMessage] = []

    for itm in raw:
        # basic attrs written by the fetcher
        snippet  = itm.get("snippet", "")
        subject  = itm.get("subject", "(No subject)")
        sender   = itm.get("sender", "")
        date_iso = itm.get("dateISO")

        # if any of those are missing, parse them from the stored raw thread json
        if not (subject and sender and date_iso):
            try:
                thread = json.loads(itm["raw"])
                first  = (thread.get("messages") or thread.get("payload") or [])[0]
                hdrs   = _hdrs_to_dict(first.get("payload", {}).get("headers", []))
                subject  = subject  or hdrs.get("subject", subject)
                sender   = sender   or hdrs.get("from",    sender)
                if not date_iso and (raw_dt := hdrs.get("date")):
                    try:
                        date_iso = parsedate_to_datetime(raw_dt).isoformat()
                    except Exception:
                        pass
            except Exception:
                pass

        out.append(
            GmailMessage(
                MessageID   = itm["MessageID"],
                snippet     = snippet,
                subject     = subject,
                sender      = sender,
                senderEmail = sender.split("<")[-1].strip("> ") if "<" in sender else sender,
                dateISO     = date_iso,
                plain       = itm.get("plain"),
                html        = itm.get("html"),
                urgent      = itm.get("urgent", False),
                aiSummary   = itm.get("aiSummary", []),
                aiChecklist = itm.get("aiChecklist", []),
            )
        )

    # newest first
    out.sort(key=lambda m: m.dateISO or "", reverse=True)
    return out
