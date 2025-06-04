"""
Gmail OAuth 2.0, cache-sync, and list-view (multi-account).

Endpoints
=========

GET  /gmail/connect     → Google consent URL  
GET  /gmail/callback    → stores token under  gmail:<addr>  
POST /gmail/fetch       → pulls newest threads for *all* Gmail accounts  
GET  /gmail/messages    → merged cached view (for React list)  
GET  /gmail/accounts    → list of addresses  ["me@x", "other@y"]
"""
from __future__ import annotations

import json, os
from email.utils import parsedate_to_datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.core.auth import current_user
from app.core.db   import (
    list_msgs,
    save_token,
    list_gmail_tokens,
)
from app.core.secrets import get as get_secret
from . import service
from .schemas import GmailMessage

router = APIRouter(prefix="/gmail", tags=["gmail"])

# ───────────────────────── configuration ─────────────────────────
SECRET = get_secret("gmail-oauth")
SCOPES = os.getenv(
    "GMAIL_SCOPES", "https://www.googleapis.com/auth/gmail.readonly"
).split(",")


def _detect_redirect() -> str:
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


def _hdrs_to_dict(h: list[dict]) -> dict[str, str]:
    return {i["name"].lower(): i["value"] for i in h}


# ───────────────────────── OAuth endpoints ───────────────────────
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
    • Exchange auth-code → tokens  
    • Discover the Gmail address just authorised  
    • Store tokens keyed by ``gmail:<addr>``  
    • Prime the cache so the UI has data instantly
    """
    flow = _flow(state)
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Token exchange failed: {exc}")

    creds = flow.credentials

    # —— determine the primary Gmail address ————————————————
    email_addr = None
    try:
        gsvc = build("gmail", "v1", credentials=creds, cache_discovery=False)
        email_addr = gsvc.users().getProfile(userId="me").execute().get("emailAddress")
    except Exception:
        pass

    provider_key = f"gmail:{email_addr}" if email_addr else "gmail"

    save_token(
        state,
        provider_key,
        {
            "refresh_token": creds.refresh_token,
            "access_token":  creds.token,
            "expires_at":    int(creds.expiry.timestamp()),
            "token_uri":     creds.token_uri,
            "client_id":     SECRET["client_id"],
            "client_secret": SECRET["client_secret"],
            "scopes":        creds.scopes,
            "email":         email_addr,
        },
    )

    # —— prime the cache for *all* Gmail accounts of this user ————
    service.fetch_for_user(state, max_threads=40)

    fe = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{fe.rstrip('/')}/connected?provider=gmail")


# ───────────────────────── manual refresh (Refresh-btn) ───────────
@router.post("/fetch")
async def fetch_now(limit: int | None = 30, user=Depends(current_user)):
    """
    Hit Google for each connected account, store unseen threads,
    return the number of genuinely-new rows inserted.
    """
    new_threads = service.fetch_for_user(user["sub"], max_threads=limit or 30)
    return {"fetched": len(new_threads)}


# ───────────────────────── cached list view ───────────────────────
@router.get("/messages", response_model=List[GmailMessage])
async def list_messages(limit: int = 50, user=Depends(current_user)):
    raw = list_msgs(user["sub"], limit)
    out: list[GmailMessage] = []

    for itm in raw:
        subject  = itm.get("subject") or "(No subject)"
        sender   = itm.get("sender", "")
        date_iso = itm.get("dateISO")

        if not (sender and date_iso):                       # repair legacy rows
            try:
                thread = json.loads(itm.get("raw", "{}"))
                first  = (thread.get("messages") or thread.get("payload") or [])[0]
                hdrs   = _hdrs_to_dict(first.get("payload", {}).get("headers", []))
                sender  = sender  or hdrs.get("from", sender)
                subject = subject or hdrs.get("subject", subject)
                if not date_iso and (d := hdrs.get("date")):
                    date_iso = parsedate_to_datetime(d).isoformat()
            except Exception:
                pass

        out.append(
            GmailMessage(
                MessageID   = itm["MessageID"],
                snippet     = itm.get("snippet", ""),
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


# ───────────────────────── sidebar helper ─────────────────────────
@router.get("/accounts")
async def list_accounts(user=Depends(current_user)):
    """
    Return every Gmail address the user attached – uses cached values
    stored in triagely-oauth.
    """
    addrs: list[str] = []
    for tok in list_gmail_tokens(user["sub"]):
        data = json.loads(tok["token"])
        if data.get("email"):
            addrs.append(data["email"])
    return addrs