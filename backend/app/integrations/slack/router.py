# backend/app/integrations/slack/router.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
import os, httpx
from urllib.parse import urlencode

from app.core.auth    import current_user
from app.core.db      import save_token
from app.core.secrets import get as get_secret

router = APIRouter(prefix="/slack", tags=["slack"])

SECRET        = get_secret("slack-oauth")
CLIENT_ID     = SECRET["client_id"]
CLIENT_SECRET = SECRET["client_secret"]
SCOPES        = os.getenv("SLACK_SCOPES", "").split(",")
REDIRECT_URL  = os.getenv("SLACK_REDIRECT_URL")
FRONTEND_URL  = os.getenv("FRONTEND_URL")
OAUTH_URL     = "https://slack.com/oauth/v2/authorize"
TOKEN_URL     = "https://slack.com/api/oauth.v2.access"

@router.get("/connect")
async def connect(user=Depends(current_user)):
    qs = urlencode({
      "client_id":    CLIENT_ID,
      "scope":        ",".join(SCOPES),
      "redirect_uri": REDIRECT_URL,
      "state":        user["sub"],
    })
    return {"auth_url": f"{OAUTH_URL}?{qs}"}

@router.get("/callback")
async def callback(code: str, state: str):
    async with httpx.AsyncClient() as client:
        res = await client.post(TOKEN_URL, data={
            "code":          code,
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri":  REDIRECT_URL,
        })
    data = res.json()
    if not data.get("ok"):
        raise HTTPException(400, data.get("error"))

    save_token(state, "slack", data)
    return RedirectResponse(f"{FRONTEND_URL}/connected?provider=slack")
