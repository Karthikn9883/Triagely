"""
Called by a scheduled Lambda / cron.
Refreshes token, fetches unread threads, stores in triagely-messages.
"""
import base64, json, os, datetime, boto3, google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.core.db import get_token, put_msg

def fetch_for_user(user_id: str):
    tok = get_token(user_id, "gmail")
    if not tok: return
    creds = Credentials(
        None,
        refresh_token = tok["refresh_token"],
        token_uri     = tok["token_uri"],
        client_id     = tok["client_id"],
        client_secret = tok["client_secret"],
        scopes        = tok["scopes"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    threads = service.users().threads().list(userId="me", maxResults=20, q="is:unread").execute().get("threads",[])
    for th in threads:
        thread_data = service.users().threads().get(userId="me", id=th["id"]).execute()
        snippet = thread_data.get("snippet","")
        put_msg(user_id, f"gmail-{th['id']}", "gmail",
                {"snippet": snippet, "raw": json.dumps(thread_data)})
