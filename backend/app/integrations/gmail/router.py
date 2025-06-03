# app/integrations/gmail/router.py
# ─────────────────────────────────────────────────────────────
"""
Routes for Gmail OAuth 2.0  +  listing / refreshing cached Gmail threads
"""
from __future__ import annotations

import json
import os
from email.utils import parsedate_to_datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from app.core.auth    import current_user
from app.core.db      import list_msgs, save_token
from app.core.secrets import get as get_secret

from . import service                         # <-- our fetcher / saver
from .schemas import GmailMessage

router = APIRouter(prefix="/gmail", tags=["gmail"])

# ───────────────────────────────
# Config
# ───────────────────────────────
SECRET  = get_secret("gmail-oauth")
SCOPES  = os.getenv(
    "GMAIL_SCOPES", "https://www.googleapis.com/auth/gmail.readonly"
).split(",")


def _detect_redirect() -> str:
    # env-override → docker variables → localhost
    if (uri := os.getenv("GMAIL_REDIRECT_URL")):
        return uri.rstrip("/")
    host = os.getenv("API_HOST", "localhost")
    port = os.getenv("API_PORT", "8000")
    return f"http://{host}:{port}/gmail/callback"


REDIRECT_URI = _detect_redirect()


def _flow(state: str | None):
    return Flow.from_client_config(
        {
            "web": {
                "client_id":     SECRET["client_id"],
                "client_secret": SECRET["client_secret"],
                "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                "token_uri":     "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state=state,
    )


def _hdrs_to_dict(l: list[dict]) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in l}


# ───────────────────────────────
# OAuth  endpoints
# ───────────────────────────────
@router.get("/connect")
async def connect(user=Depends(current_user)):
    auth_url, _ = _flow(user["sub"]).authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    return {"auth_url": auth_url}


@router.get("/callback")
async def callback(request: Request, state: str = "", code: str = ""):
    """
    1. Exchange auth-code for refresh / access tokens  
    2. Persist tokens (triagely-oauth)  
    3. Immediately call `service.fetch_for_user` so the very first batch of
       threads lands in triagely-messages **before** we redirect the SPA.
    """
    flow = _flow(state)
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Token exchange failed: {exc}")

    creds = flow.credentials
    save_token(
        state,
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

    # ⭐ NEW: prime the cache so UI has data right away
    fetched = service.fetch_for_user(state, max_threads=30)
    print(f"[gmail/callback] Cached {len(fetched)} threads for user {state}")

    frontend = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{frontend.rstrip('/')}/connected?provider=gmail")


# ───────────────────────────────
# Manual refresh  (used by “Refresh” button)
# ───────────────────────────────
@router.post("/fetch")
async def fetch_now(limit: int | None = 25, user=Depends(current_user)):
    fetched = service.fetch_for_user(user["sub"], max_threads=limit or 25)
    cached  = len(list_msgs(user["sub"], limit or 100))
    return {"fetched": len(fetched), "cached": cached}


# ───────────────────────────────
# List cached threads for the SPA
# ───────────────────────────────
@router.get("/messages", response_model=List[GmailMessage])
async def list_messages(limit: int = 50, user=Depends(current_user)):
    raw_items = list_msgs(user["sub"], limit)
    out: list[GmailMessage] = []

    for itm in raw_items:
        subject  = itm.get("subject") or "(No subject)"
        sender   = itm.get("sender", "")
        date_iso = itm.get("dateISO")
        snippet  = itm.get("snippet", "")

        # fill gaps from raw JSON (if stored by previous versions)
        if not (sender and date_iso):
            try:
                thread = json.loads(itm.get("raw", "{}"))
                first  = (thread.get("messages") or thread.get("payload") or [])[0]
                hdrs   = _hdrs_to_dict(first.get("payload", {}).get("headers", []))
                sender   = sender   or hdrs.get("from", sender)
                subject  = subject  or hdrs.get("subject", subject)
                if not date_iso and (d := hdrs.get("date")):
                    try:
                        date_iso = parsedate_to_datetime(d).isoformat()
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

    out.sort(key=lambda m: m.dateISO or "", reverse=True)
    return out