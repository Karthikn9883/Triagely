from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
import os, json, hmac, hashlib, httpx
from urllib.parse import urlencode
from app.core.auth import current_user
from app.core.db import save_token
from app.core.secrets import get as get_secret

router = APIRouter(prefix="/slack", tags=["slack"])
SECRET = get_secret("slack-oauth")
CLIENT_ID, CLIENT_SECRET = SECRET["client_id"], SECRET["client_secret"]
SIGNING_SECRET = SECRET["signing_secret"]

SCOPES     = os.getenv("SLACK_SCOPES","channels:read,channels:history,im:history").split(",")
REDIRECT   = os.getenv("SLACK_REDIRECT_URL")
OAUTH_URL  = "https://slack.com/oauth/v2/authorize"
TOKEN_URL  = "https://slack.com/api/oauth.v2.access"

@router.get("/connect")
async def connect(user=Depends(current_user)):
    qs = urlencode({
        "client_id": CLIENT_ID,
        "scope": ",".join(SCOPES),
        "redirect_uri": REDIRECT,
        "state": user["sub"]
    })
    return {"auth_url": f"{OAUTH_URL}?{qs}"}

@router.get("/callback")
async def callback(code: str, state: str):
    async with httpx.AsyncClient() as c:
        res = await c.post(TOKEN_URL, data={
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT
        })
    data = res.json()
    if not data.get("ok"):
        raise HTTPException(400, data.get("error"))
    save_token(state, "slack", data)   # full JSON inc. access_token, etc.
    return RedirectResponse("/connected?provider=slack")

@router.post("/events")
async def events(request: Request):
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp","0")
    sig_basestr = f"v0:{timestamp}:{body.decode()}"
    my_sig = "v0=" + hmac.new(SIGNING_SECRET.encode(), sig_basestr.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(my_sig, request.headers.get("X-Slack-Signature","")):
        raise HTTPException(403, "Bad signature")
    payload = await request.json()
    if payload.get("type") == "url_verification":
        return JSONResponse({"challenge": payload["challenge"]})
    # TODO: enqueue message events for processing
    return JSONResponse({"ok": True})
