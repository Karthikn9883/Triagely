import os
import base64
import email
import datetime as dt
import re
import boto3
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from botocore.exceptions import ClientError

# DynamoDB tables
dynamodb     = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION"))
tbl_oauth    = dynamodb.Table("triagely-oauth")
tbl_messages = dynamodb.Table("triagely-messages")

URGENT_RE = re.compile(r"\b(urgent|overdrawn|asap|immediately|action required)\b", re.I)

def _get_creds(user_id: str) -> Credentials | None:
    try:
        item = tbl_oauth.get_item(Key={"UserID": user_id, "Provider": "gmail"})["Item"]
    except KeyError:
        return None

    creds = Credentials(
        item.get("access_token"),
        refresh_token=item.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=item.get("client_id"),
        client_secret=item.get("client_secret"),
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        tbl_oauth.update_item(
            Key={"UserID": user_id, "Provider": "gmail"},
            UpdateExpression="SET access_token = :t, expires_at = :e",
            ExpressionAttributeValues={
                ":t": creds.token,
                ":e": int(creds.expiry.timestamp()),
            },
        )
    return creds

def extract_message_details(msg_payload):
    subject = sender = ""
    plain_body = html_body = ""

    # Headers
    headers = {h["name"].lower(): h["value"] for h in msg_payload.get("headers", [])}
    subject = headers.get("subject", "(No subject)")
    sender  = headers.get("from", "(Unknown)")

    # Recursive part walker
    def walk_parts(part):
        nonlocal plain_body, html_body
        mime_type = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if data:
            try:
                decoded = base64.urlsafe_b64decode(data + '=' * (-len(data) % 4)).decode("utf-8", errors="ignore")
                if mime_type.startswith("text/plain") and not plain_body:
                    plain_body = decoded
                elif mime_type.startswith("text/html") and not html_body:
                    html_body = decoded
            except Exception:
                pass
        for sub in part.get("parts", []):
            walk_parts(sub)
    walk_parts(msg_payload)
    return subject, sender, plain_body, html_body

def _save_message(user_id: str, m: dict) -> None:
    try:
        tbl_messages.put_item(
            Item={"UserID": user_id, **m},
            ConditionExpression="attribute_not_exists(MessageID)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise

def fetch_for_user(user_id: str, max_threads: int = 25) -> list[dict]:
    creds = _get_creds(user_id)
    if not creds:
        return []
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    threads = (
        service.users()
        .threads()
        .list(userId="me", maxResults=max_threads, q="in:anywhere")
        .execute()
        .get("threads", [])
    )

    out: list[dict] = []
    for t in threads:
        tid = t["id"]
        g_thread = service.users().threads().get(userId="me", id=tid, format="full").execute()
        msg0 = g_thread["messages"][0]

        subject, sender, plain, html = extract_message_details(msg0["payload"])
        print(f"SAVING MSG: subject={subject} sender={sender} plain?={bool(plain)} html?={bool(html)}")

        date_raw = ""
        for h in msg0["payload"]["headers"]:
            if h["name"].lower() == "date":
                date_raw = h["value"]
                break
        try:
            date_iso = email.utils.parsedate_to_datetime(date_raw).isoformat() if date_raw else ""
        except Exception:
            date_iso = ""

        m = {
            "MessageID": tid,
            "subject": subject,
            "sender": sender,
            "snippet": msg0.get("snippet", plain[:120]),
            "dateISO": date_iso,
            "plain": plain,
            "html": html,
            "urgent": bool(URGENT_RE.search(subject)),
            "aiSummary": [],
            "aiChecklist": [],
        }
        _save_message(user_id, m)
        out.append(m)
    out.sort(key=lambda x: x["dateISO"], reverse=True)
    return out
