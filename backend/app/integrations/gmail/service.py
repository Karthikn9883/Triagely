"""
Triagely · Gmail service layer (multi-account aware)
Fetches threads, stores unseen ones, returns # inserted.
"""
from __future__ import annotations
import base64, datetime as dt, email, json, os, re
from typing import Any, List
import boto3
from botocore.exceptions import ClientError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from boto3.dynamodb.conditions import Key, Attr
from app.core.db import put_msg, list_gmail_tokens, save_token       # helpers

dynamodb   = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION"))
tbl_oauth  = dynamodb.Table("triagely-oauth")

URGENT_RE   = re.compile(r"\b(urgent|overdrawn|asap|immediately|action required)\b", re.I)
B64URLPAD   = lambda s: s + "=" * (4 - len(s) % 4)

# ─────────────────────────────────────────────────────────────────────────────
def _get_creds(row: dict) -> Credentials:
    tok = json.loads(row["token"])
    creds = Credentials(
        tok.get("access_token"),
        refresh_token = tok.get("refresh_token"),
        token_uri     = tok.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id     = tok.get("client_id"),
        client_secret = tok.get("client_secret"),
        scopes        = tok.get("scopes", ["https://www.googleapis.com/auth/gmail.readonly"]),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        tok["access_token"] = creds.token
        tbl_oauth.update_item(                     # persist fresh access token
            Key={"UserID": row["UserID"], "Provider": row["Provider"]},
            UpdateExpression="SET token = :t",
            ExpressionAttributeValues={":t": json.dumps(tok)},
        )
    return creds

def _mime_parts(payload: dict[str, Any]) -> tuple[str, str]:
    plain, html = "", ""
    def walk(p):
        nonlocal plain, html
        mt = p.get("mimeType", "")
        data = p.get("body", {}).get("data")
        if data:
            try:
                decoded = base64.urlsafe_b64decode(B64URLPAD(data)).decode("utf-8", errors="ignore")
            except Exception:
                decoded = ""
            if mt.startswith("text/plain") and not plain:
                plain = decoded
            elif mt.startswith("text/html") and not html:
                html = decoded
        for sub in p.get("parts", []):
            walk(sub)
    walk(payload)
    return plain, html

# --------------------------------------------------------------------------- #
# Public: fetch_for_user                                                      #
# --------------------------------------------------------------------------- #
def fetch_for_user(
    user_id: str,
    provider_key: str | None = None,
    *,
    max_threads: int = 40,
) -> int:
    """
    • If provider_key is None → poll *every* gmail:<addr> the user has.  
    • Else                        → poll just that one account.

    Returns **number of brand-new threads inserted**.
    """
    if provider_key:
        token_rows: List[dict] = [
            tbl_oauth.get_item(Key={"UserID": user_id, "Provider": provider_key})["Item"]
        ]
    else:
        token_rows = list_gmail_tokens(user_id)          # helper in app/core/db.py

    new_rows = 0

    for row in token_rows:
        creds = _get_creds(row)
        address = row["Provider"].split("gmail:")[-1] or "unknown"
        g = build("gmail", "v1", credentials=creds, cache_discovery=False)

        try:
            resp = (
                g.users()
                 .threads()
                 .list(userId="me", maxResults=max_threads, q="in:anywhere")
                 .execute()
            )
        except Exception as exc:
            print("[gmail] list() failed:", exc)
            continue

        for th in resp.get("threads", []):
            tid      = th["id"]
            msg_key  = f"gmail-{address}-{tid}"        # globally unique ID

            # already cached?
            try:
                dynamodb.Table("triagely-messages").get_item(
                    Key={"UserID": user_id, "MessageID": msg_key}
                )["Item"]
                continue
            except KeyError:
                pass

            # pull full thread once
            full = g.users().threads().get(userId="me", id=tid, format="full").execute()
            msg0 = full["messages"][0]
            hdr  = {h["name"]: h["value"] for h in msg0["payload"].get("headers", [])}
            subj = hdr.get("Subject", "(no subject)")
            sender = hdr.get("From", "(unknown)")
            try:
                date_iso = email.utils.parsedate_to_datetime(hdr.get("Date", "")).isoformat()
            except Exception:
                date_iso = dt.datetime.utcnow().isoformat()

            plain, html = _mime_parts(msg0["payload"])
            snippet = msg0.get("snippet", plain[:120])

            body = {
                "subject":   subj,
                "snippet":   snippet,
                "sender":    sender,
                "dateISO":   date_iso,
                "plain":     plain,
                "html":      html,
                "urgent":    bool(URGENT_RE.search(subj)),
                "aiSummary": [],
                "aiChecklist": [],
            }

            if put_msg(user_id, msg_key, body):
                new_rows += 1

    return new_rows


# --------------------------------------------------------------------------- #
# Helper for LLM layer                                                        #
# --------------------------------------------------------------------------- #
def load_thread_plain(user_id: str, message_id: str) -> str:
    """
    Return the cached plain-text body for a message/thread.
    Falls back to snippet if plain is empty.  Returns '' if not found.
    """
    try:
        item = dynamodb.Table("triagely-messages").get_item(
            Key={"UserID": user_id, "MessageID": message_id}
        )["Item"]
        return item.get("plain") or item.get("snippet", "")
    except KeyError:
        return ""
