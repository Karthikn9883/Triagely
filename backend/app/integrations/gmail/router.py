# app/integrations/gmail/router.py

"""
Gmail integration router for Triagely backend.
Handles OAuth flows, token storage, cache priming, manual refresh,
listing cached messages, and listing connected Gmail accounts.
"""
from __future__ import annotations

import json
import os
from email.utils import parsedate_to_datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Import auth dependency to secure endpoints
from app.core.auth import current_user
# Database helpers: list messages, save OAuth token, list Gmail tokens
from app.core.db import (
    list_msgs,
    save_token,
    list_gmail_tokens,
)
# Service layer for fetching and syncing messages
from . import service
# Pydantic schema for serializing message list responses
from .schemas import GmailMessage

# Create a router with prefix '/gmail' and OpenAPI tag 'gmail'
router = APIRouter(prefix="/gmail", tags=["gmail"])

# ───────────────────────── configuration ─────────────────────────
# Load OAuth client ID/secret from environment variables
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
# Scopes to request from Google; defaults to readonly
SCOPES = os.getenv(
    "GMAIL_SCOPES", "https://www.googleapis.com/auth/gmail.readonly"
).split(",")


def _detect_redirect() -> str:
    """
    Determine redirect URI for OAuth callback:
      1) Use GMAIL_REDIRECT_URL env var if set (rstrip trailing slash)
      2) Otherwise fallback to http://API_HOST:API_PORT/gmail/callback
    """
    if (uri := os.getenv("GMAIL_REDIRECT_URL")):
        return uri.rstrip("/")
    host = os.getenv("API_HOST", "localhost")
    port = os.getenv("API_PORT", "8000")
    return f"http://{host}:{port}/gmail/callback"

# Final OAuth redirect URL
REDIRECT_URI = _detect_redirect()


def _flow(state: str | None):
    """
    Create a google_auth_oauthlib Flow instance configured with:
      - client_id / client_secret from SECRET
      - requested SCOPES
      - redirect_uri set above
      - state parameter (Cognito user sub) to tie callback to user
    """
    return Flow.from_client_config(
        {
            "web": {
                "client_id":     GMAIL_CLIENT_ID,
                "client_secret": GMAIL_CLIENT_SECRET,
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
    """
    Convert Gmail API header list to a dict mapping lowercase names to values.
    Used for repairing legacy stored messages without explicit fields.
    """
    return {i["name"].lower(): i["value"] for i in h}

# ───────────────────────── OAuth endpoints ───────────────────────
@router.get("/connect")
async def connect(user=Depends(current_user)):
    """
    Initiates OAuth by returning the Google consent URL.
    - The `state` parameter is the Cognito user sub, so we know which
      user to associate the token with when Google redirects back.
    """
    auth_url, _ = _flow(user["sub"]).authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    return {"auth_url": auth_url}

@router.get("/callback")
async def callback(request: Request, state: str = "", code: str = ""):
    """
    Handles OAuth callback:
      1) Exchange `code` for tokens
      2) Use Gmail API to fetch authorized email address
      3) Save tokens in Dynamo under PK=state (user_sub), SK="gmail:<addr>"
      4) Prime the cache by pulling messages immediately
      5) Redirect back to front-end connected screen
    """
    flow = _flow(state)
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {exc}")

    creds = flow.credentials

    # Determine the user's Gmail address via profile API
    email_addr = None
    try:
        gsvc = build("gmail", "v1", credentials=creds, cache_discovery=False)
        email_addr = gsvc.users().getProfile(userId="me").execute().get("emailAddress")
    except Exception:
        # If profile call fails, we'll still store the token under 'gmail'
        pass

    provider_key = f"gmail:{email_addr}" if email_addr else "gmail"

    # Persist token JSON in oauth_tokens table for this user & provider
    save_token(
        state,
        provider_key,
        {
            "refresh_token": creds.refresh_token,
            "access_token":  creds.token,
            "expires_at":    int(creds.expiry.timestamp()),
            "token_uri":     creds.token_uri,
            "client_id":     GMAIL_CLIENT_ID,
            "client_secret": GMAIL_CLIENT_SECRET,
            "scopes":        creds.scopes,
            "email":         email_addr,
        },
    )

    # Immediately fetch all emails from past 60 days (but don't process with AI yet)
    service.fetch_for_user(state, full_sync=True)

    # Process only the first 3 most recent emails with AI to save API costs
    service.process_first_emails_with_ai(state, count=3)

    # Redirect the browser back to the React front-end
    fe = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(f"{fe.rstrip('/')}/connected?provider=gmail")

# ───────────────────────── manual refresh (Refresh-btn) ───────────
@router.post("/fetch")
async def fetch_now(user=Depends(current_user)):
    """
    Manually trigger a complete 90-day cache sync:
      • Calls service.fetch_for_user with full_sync=True to pull ALL threads from past 90 days
      • Returns the count of newly-inserted threads
    """
    count = service.fetch_for_user(user["sub"], full_sync=True)
    return {"fetched": count, "message": "Full 90-day sync completed"}

@router.post("/full-sync")
async def full_sync(user=Depends(current_user)):
    """
    Manually trigger a complete 90-day sync:
      • Fetches ALL emails from past 90 days using pagination
      • May take several minutes for accounts with many emails
      • Returns the count of newly-inserted threads
    """
    count = service.fetch_for_user(user["sub"], full_sync=True)
    return {"fetched": count, "message": "Full 90-day sync completed"}

# ───────────────────────── cached list view ───────────────────────
@router.get("/messages")
async def list_messages(limit: int = 50, page: int = 1, user=Depends(current_user)):
    """
    Returns a paginated view of cached threads for this user.
    - Reads up to `limit` items from triagely-messages Dynamo table per page
    - Repairs legacy rows missing subject/sender/date via raw JSON -> headers
    - Serializes into `GmailMessage` Pydantic models
    - Returns pagination metadata
    """
    result = list_msgs(user["sub"], limit, page)
    raw = result["items"]
    out: list[GmailMessage] = []

    for itm in raw:
        # Extract preview fields, with fallbacks
        subject  = itm.get("subject") or "(No subject)"
        sender   = itm.get("sender", "")
        date_iso = itm.get("dateISO")

        # Repair any legacy entry missing sender or date
        if not (sender and date_iso):
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

        # Append a fully-populated Pydantic model for API response
        out.append(
            GmailMessage(
                MessageID   = itm["MessageID"],
                snippet     = itm.get("snippet", ""),
                subject     = subject,
                sender      = sender,
                senderEmail = itm.get("senderEmail"),
                dateISO     = date_iso,
                plain       = itm.get("plain"),
                html        = itm.get("html"),
                priority    = itm.get("priority", "Normal"),
                aiSummary   = itm.get("aiSummary", []),
                aiChecklist = itm.get("aiChecklist", []),
                account     = itm.get("account"),
            )
        )

    # Sort newest-first by ISO date string
    out.sort(key=lambda m: m.dateISO or "", reverse=True)
    
    # Return paginated response with metadata
    return {
        "data": out,
        "pagination": result["pagination"]
    }

# ───────────────────────── priority messages ─────────────────────────
@router.get("/priority-messages")
async def list_priority_messages(limit: int = 50, page: int = 1, user=Depends(current_user)):
    """
    Returns high priority messages only for the current user.
    - Uses efficient DynamoDB filtering for priority='High'
    - Reads from triagely-messages DynamoDB table
    - Repairs legacy rows and serializes into GmailMessage models
    """
    result = list_msgs(user["sub"], limit, page, priority_filter="High")
    raw = result["items"]
    out: list[GmailMessage] = []

    for itm in raw:
        # Extract preview fields, with fallbacks
        subject  = itm.get("subject") or "(No subject)"
        sender   = itm.get("sender", "")
        date_iso = itm.get("dateISO")

        # Repair any legacy entry missing sender or date
        if not (sender and date_iso):
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

        # Append a fully-populated Pydantic model for API response
        out.append(
            GmailMessage(
                MessageID   = itm["MessageID"],
                snippet     = itm.get("snippet", ""),
                subject     = subject,
                sender      = sender,
                senderEmail = itm.get("senderEmail"),
                dateISO     = date_iso,
                plain       = itm.get("plain"),
                html        = itm.get("html"),
                priority    = itm.get("priority", "Normal"),
                aiSummary   = itm.get("aiSummary", []),
                aiChecklist = itm.get("aiChecklist", []),
                account     = itm.get("account"),
            )
        )

    # Data is already sorted by the database query
    return {
        "data": out,
        "pagination": result["pagination"]
    }

# ───────────────────────── sidebar helper ─────────────────────────
@router.get("/accounts")
async def list_accounts(user=Depends(current_user)):
    """
    Return the list of connected Gmail addresses for the current user.
    - Queries triagely-oauth table for rows with 'gmail:' prefix
    - Pulls email field from stored token JSON
    """
    addrs: list[str] = []
    for tok in list_gmail_tokens(user["sub"]):
        data = json.loads(tok["token"]);
        if data.get("email"):
            addrs.append(data.get("email"))
    return addrs
