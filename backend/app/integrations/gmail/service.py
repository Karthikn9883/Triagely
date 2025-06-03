# app/integrations/gmail/service.py
# ─────────────────────────────────────────────────────────────────────────────
# Triagely · Gmail service layer
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import base64
import datetime as dt
import email
import json
import os
import re
from typing import Any

import boto3
from botocore.exceptions import ClientError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ─────────────────────────────────────────────────────────────────────────────
# DynamoDB tables
# ─────────────────────────────────────────────────────────────────────────────
dynamodb     = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION"))
tbl_oauth    = dynamodb.Table("triagely-oauth")      # PK = UserID,  SK = "gmail"
tbl_messages = dynamodb.Table("triagely-messages")   # PK = UserID,  SK = MessageID

# ─────────────────────────────────────────────────────────────────────────────
# Regex and helpers
# ─────────────────────────────────────────────────────────────────────────────
URGENT_RE = re.compile(r"\b(urgent|overdrawn|asap|immediately|action required)\b", re.I)
B64URLPAD = lambda s: s + "=" * (4 - len(s) % 4)   # Gmail’s base64 is URL-safe without padding


def _get_creds(user_id: str) -> Credentials | None:
    """
    Pull the stored OAuth JSON from DynamoDB under the "token" attribute,
    parse it, then return a google.oauth2.credentials.Credentials instance.
    """
    try:
        # Fetch exactly the item we saved in /gmail/callback
        resp = tbl_oauth.get_item(Key={"UserID": user_id, "Provider": "gmail"})
        item = resp["Item"]
    except KeyError:
        return None

    # The raw token is stored as a JSON‐string under "token"
    raw_token_json = item.get("token")
    if not raw_token_json:
        return None

    # Convert that JSON‐string to a Python dict
    try:
        tok: dict[str, Any] = json.loads(raw_token_json)
    except Exception:
        return None

    # Now build a Credentials object from the fields inside that dict
    # Gmail expects: access_token, refresh_token, token_uri, client_id, client_secret, scopes
    creds = Credentials(
        tok.get("access_token"),             # initial (possibly expired) access token
        refresh_token=tok.get("refresh_token"),
        token_uri=tok.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=tok.get("client_id"),
        client_secret=tok.get("client_secret"),
        scopes=tok.get("scopes", ["https://www.googleapis.com/auth/gmail.readonly"]),
    )

    # If that access_token is expired, refresh() will fetch a new one
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

        # Persist the new access_token and expiry time back to DynamoDB
        try:
            tbl_oauth.update_item(
                Key={"UserID": user_id, "Provider": "gmail"},
                UpdateExpression="SET token = :t",
                ExpressionAttributeValues={
                    # Overwrite the entire token JSON with a fresh copy
                    # so that "access_token" and "expires_at" are up to date.
                    ":t": json.dumps({
                        "refresh_token": creds.refresh_token,
                        "access_token":  creds.token,
                        "expires_at":    int(creds.expiry.timestamp()),
                        "token_uri":     tok.get("token_uri"),
                        "client_id":     tok.get("client_id"),
                        "client_secret": tok.get("client_secret"),
                        "scopes":        tok.get("scopes"),
                    })
                },
            )
        except ClientError as exc:
            # If DynamoDB update fails, log it (print or your preferred logger)
            print("Failed to update refreshed token:", exc)

    return creds


def _mime_parts(msg_payload: dict[str, Any]) -> tuple[str, str]:
    """
    Walk the Gmail API 'payload' structure and pick out text/plain and text/html.
    Returns (plain_text, html_text), whichever were found first.
    """
    plain, html = "", ""

    def recurse(part: dict[str, Any]) -> None:
        nonlocal plain, html

        mime_type = part.get("mimeType", "")
        data      = part.get("body", {}).get("data")
        if data:
            # Gmail data is base64url without padding, so re‐pad and decode
            try:
                decoded = base64.urlsafe_b64decode(B64URLPAD(data)).decode("utf-8", errors="ignore")
            except Exception:
                decoded = ""
            if mime_type.startswith("text/plain") and not plain:
                plain = decoded
            elif mime_type.startswith("text/html") and not html:
                html = decoded

        for sub_part in part.get("parts", []):
            recurse(sub_part)

    recurse(msg_payload)
    return plain, html


def _save_message(user_id: str, m: dict[str, Any]) -> None:
    """
    Idempotent write into DynamoDB: only insert if that MessageID does not exist for this user.
    """
    try:
        tbl_messages.put_item(
            Item={"UserID": user_id, **m},
            ConditionExpression="attribute_not_exists(MessageID)",
        )
    except ClientError as e:
        # Ignore “already exists” errors; re‐throw others
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise


def fetch_for_user(user_id: str, max_threads: int = 25) -> list[dict]:
    """
    Fetch the latest Gmail threads for this user, store them into DynamoDB,
    and return a Python list of “clean” message dicts that the frontend can consume.
    """
    creds = _get_creds(user_id)
    if not creds:
        return []

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    # List the user’s threads (adjust the query as you like—“in:anywhere” returns all)
    resp = (
        service.users()
        .threads()
        .list(userId="me", maxResults=max_threads, q="in:anywhere")
        .execute()
    )
    threads = resp.get("threads", [])
    out: list[dict] = []

    for t in threads:
        tid = t["id"]
        g_thread = service.users().threads().get(
            userId="me", id=tid, format="full"
        ).execute()

        # We’ll only display the very first message in that thread
        # (you can modify to combine all messages in a thread if you wish)
        msg0 = g_thread["messages"][0]

        # Extract headers into a dict
        hdr_map = { h["name"]: h["value"] for h in msg0["payload"].get("headers", []) }
        subject  = hdr_map.get("Subject", "(no subject)")
        sender   = hdr_map.get("From", "(unknown)")
        date_raw = hdr_map.get("Date", "")
        try:
            date_iso = email.utils.parsedate_to_datetime(date_raw).isoformat()
        except Exception:
            date_iso = dt.datetime.utcnow().isoformat()

        # Walk the MIME parts to find text/plain and text/html
        plain, html = _mime_parts(msg0["payload"])
        snippet     = msg0.get("snippet", plain[:120])

        # Build our “mini‐message” structure
        m = {
            "MessageID":   tid,
            "subject":     subject,
            "snippet":     snippet,
            "sender":      sender,
            "dateISO":     date_iso,
            "plain":       plain,
            "html":        html,
            "urgent":      bool(URGENT_RE.search(subject)),
            "aiSummary":   [],  # stubs for future NLP
            "aiChecklist": [],
        }

        # Write to Dynamo (only if new)
        _save_message(user_id, m)
        out.append(m)

    # Sort newest-first
    out.sort(key=lambda x: x["dateISO"], reverse=True)
    return out