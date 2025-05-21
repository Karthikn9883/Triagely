import httpx, os, time
from app.core.db import get_token, put_msg

SLACK_API = "https://slack.com/api/"

async def fetch_for_user(user_id: str):
    tok = get_token(user_id, "slack")
    if not tok: return
    token = tok["access_token"]
    async with httpx.AsyncClient() as c:
        ch = (await c.get(SLACK_API+"conversations.list",
                          params={"types":"public_channel,im"},
                          headers={"Authorization": f"Bearer {token}"})).json().get("channels",[])
        for channel in ch:
            hist = (await c.get(SLACK_API+"conversations.history",
                                params={"channel": channel["id"], "limit": 20},
                                headers={"Authorization": f"Bearer {token}"})).json()
            for msg in hist.get("messages", []):
                ts = msg["ts"].replace(".","")
                put_msg(user_id, f"slack-{channel['id']}-{ts}", "slack", msg)
