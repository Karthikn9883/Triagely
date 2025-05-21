from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
import os, json, httpx
from app.core.auth import current_user
from app.core.db import save_token
from app.core.secrets import get as get_secret

router = APIRouter(prefix="/gmail", tags=["gmail"])
SECRET = get_secret("gmail-oauth")
SCOPES = os.getenv("GMAIL_SCOPES","https://www.googleapis.com/auth/gmail.readonly").split(",")
REDIRECT = os.getenv("GMAIL_REDIRECT_URL")

def _flow(state: str | None):
    return Flow.from_client_config(
        {"web": {
            "client_id": SECRET["client_id"],
            "client_secret": SECRET["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT],
        }},
        scopes=SCOPES,
        redirect_uri=REDIRECT,
        state=state
    )

@router.get("/connect")
async def connect(user=Depends(current_user)):
    auth_url, _ = _flow(user["sub"]).authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )
    return {"auth_url": auth_url}

@router.get("/callback")
async def callback(request: Request, state: str = "", code: str = ""):
    flow = _flow(state)
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        raise HTTPException(400, f"Token exchange failed: {e}")
    creds = flow.credentials
    save_token(state, "gmail", {
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": SECRET["client_id"],
        "client_secret": SECRET["client_secret"],
        "scopes": creds.scopes
    })
    return RedirectResponse(url="/connected?provider=gmail")
