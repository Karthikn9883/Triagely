# app/integrations/gmail/service.py

"""
Gmail service layer for Triagely backend.
Handles:
  - Fetching new threads via Gmail API
  - Deduplicating against DynamoDB cache
  - Extracting plain text, HTML, and snippet
  - Running LLM to assign a High/Normal priority before persistence
  - Writing new message items into DynamoDB

Functions should be kept lean; heavy lifting (OAuth refresh, LLM call)
is delegated to helpers.
"""
from __future__ import annotations
import base64
import datetime as dt
import email
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Database helpers: create message rows, list OAuth tokens, get/save tokens
from app.core.db import put_msg, list_gmail_tokens, get_token, save_token, get_message, update_message_ai
# LLM support: provider call and prompt template for priority
from app.nlp.llm.provider import call, LLMRequest
from app.nlp.llm.priority import SYSTEM_PROMPT
# AI processing functions for summary and checklist
from app.nlp.llm.summary import summarise_thread
from app.nlp.llm.checklist import extract_checklist

# Regex to detect and restore URL-safe base64 padding
B64PAD = lambda s: s + "=" * (4 - len(s) % 4)


def _get_creds(row: dict) -> Credentials:
    """
    Build Google Credentials from stored token JSON.
    • Refresh access_token if expired (and refresh_token present).
    • Persist renewed access_token back to oauth_tokens table.

    Args:
      row: Database row dict containing 'token' JSON string.

    Returns:
      A google.oauth2.credentials.Credentials instance, ready to use.
    """
    tok = json.loads(row["token"])
    creds = Credentials(
        tok.get("access_token"),
        refresh_token = tok.get("refresh_token"),
        token_uri     = tok.get("token_uri"),
        client_id     = tok.get("client_id"),
        client_secret = tok.get("client_secret"),
        scopes        = tok.get("scopes"),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())  # Fetch new access_token
        tok["access_token"] = creds.token  # Update cached token JSON
        # Persist refresh to database
        save_token(row["UserID"], row["Provider"], tok)
    return creds


def _mime_parts(payload: dict[str, Any]) -> tuple[str, str]:
    """
    Recursively walks Gmail payload to extract the first
    text/plain and text/html parts.

    Args:
      payload: Gmail API message payload dict (full format).

    Returns:
      Tuple of (plain_text, html_text).
    """
    plain, html = "", ""
    def walk(part: dict[str, Any]):
        nonlocal plain, html
        mime_type = part.get("mimeType", "")
        data      = part.get("body", {}).get("data")
        if data:
            # Base64 decode with URL-safe padding
            try:
                txt = base64.urlsafe_b64decode(B64PAD(data)).decode("utf-8", errors="ignore")
            except Exception:
                txt = ""
            # Capture first plain or HTML block
            if mime_type.startswith("text/plain") and not plain:
                plain = txt
            elif mime_type.startswith("text/html") and not html:
                html = txt
        # Recurse into sub-parts
        for sub in part.get("parts", []):
            walk(sub)
    walk(payload)
    return plain, html


def fetch_for_user(
    user_id: str,
    provider_key: str | None = None,
    *,
    max_threads: int = 40,
    full_sync: bool = False,
    limit_emails: int | None = None,
) -> int:
    """
    Polls Gmail for new threads and caches them with LLM-prioritized metadata.

    Workflow:
      1) Determine which Gmail accounts to poll (single or all via provider_key)
      2) List threads from Gmail with date-based query
      3) For each thread not already in DynamoDB:
         a) Fetch full thread, extract headers and bodies
         b) Compute a snippet (plain first 120 chars fallback)
         c) Run LLM on plain text to decide 'High' vs 'Normal'
         d) Construct DynamoDB item including priority & account
         e) Insert via put_msg (idempotent by MessageID)

    Args:
      user_id: Cognito user sub, used as DynamoDB partition key
      provider_key: Optional sort-key for a specific gmail:<address>
      max_threads: maxResults parameter for Gmail API (ignored if full_sync=True)
      full_sync: if True, fetch all emails from past 90 days with pagination
      limit_emails: if set, only fetch this many latest emails (useful for initial sync)

    Returns:
      Number of new threads inserted into DynamoDB.
    """
    # Choose tokens based on provider_key or all Gmail tokens
    if provider_key:
        tok = get_token(user_id, provider_key)
        if not tok:
            return 0
        token_rows = [{"UserID": user_id, "Provider": provider_key, "token": json.dumps(tok)}]
    else:
        token_rows = list_gmail_tokens(user_id)

    new_rows = 0
    for row in token_rows:
        creds   = _get_creds(row)
        address = row["Provider"].split("gmail:")[-1] or "unknown"
        svc     = build("gmail", "v1", credentials=creds, cache_discovery=False)

        # 1) Determine query based on sync type
        if limit_emails:
            # Limited sync: fetch only N latest emails
            query = "newer_than:60d"
            new_rows += _fetch_single_batch(svc, user_id, address, query, limit_emails)
        elif full_sync:
            query = "newer_than:60d"
            new_rows += _fetch_with_pagination(svc, user_id, address, query)
        else:
            query = "newer_than:2d"
            new_rows += _fetch_single_batch(svc, user_id, address, query, max_threads)

    return new_rows


def process_first_emails_with_ai(user_id: str, count: int = 3) -> int:
    """
    Process the first N most recent emails with AI (summary, checklist, priority).
    This is called after initial sync to process only the most recent emails.

    Args:
      user_id: User ID to process emails for
      count: Number of most recent emails to process with AI

    Returns:
      Number of emails processed with AI
    """
    from app.core.db import list_msgs

    # Get the most recent emails
    result = list_msgs(user_id, limit=count, page=1)
    emails = result["items"]

    processed = 0
    for email in emails:
        msg_key = email["MessageID"]

        # Skip if already processed (has AI summary)
        if email.get("aiSummary") and len(email.get("aiSummary", [])) > 0:
            continue

        try:
            # Generate AI summary
            sum_res = summarise_thread(user_id, msg_key)
            ai_summary = sum_res.get("summary", [])

            # Generate AI checklist
            chk_res = extract_checklist(user_id, msg_key)
            raw_items = chk_res.get("checklist", [])
            ai_checklist = [{"text": line, "checked": False} for line in raw_items]

            # Update the message with AI results
            update_message_ai(user_id, msg_key, ai_summary, ai_checklist)
            print(f"[gmail] AI processing completed for {msg_key}")
            processed += 1

        except Exception as ai_error:
            print(f"[gmail] AI processing failed for {msg_key}: {ai_error}")

    return processed


def _fetch_single_batch(svc, user_id: str, address: str, query: str, max_results: int) -> int:
    """
    Fetch a single batch of threads (for regular polling).
    """
    try:
        resp = svc.users().threads().list(
            userId="me", maxResults=max_results, q=query
        ).execute()
    except Exception as e:
        print("[gmail] list failed:", e)
        return 0

    return _process_threads(svc, user_id, address, resp.get("threads", []))


def _fetch_with_pagination(svc, user_id: str, address: str, query: str) -> int:
    """
    Fetch all threads matching query using pagination (for full sync).
    """
    total_new = 0
    page_token = None
    max_results = 500  # Max allowed by Gmail API
    
    while True:
        try:
            list_args = {
                "userId": "me",
                "maxResults": max_results,
                "q": query
            }
            if page_token:
                list_args["pageToken"] = page_token
                
            resp = svc.users().threads().list(**list_args).execute()
        except Exception as e:
            print(f"[gmail] paginated list failed: {e}")
            break

        threads = resp.get("threads", [])
        if not threads:
            break
            
        # Process this batch of threads
        batch_new = _process_threads(svc, user_id, address, threads)
        total_new += batch_new
        
        print(f"[gmail] {address}: processed {len(threads)} threads, {batch_new} new")
        
        # Check for next page
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
            
    return total_new


def _process_threads(svc, user_id: str, address: str, threads: list) -> int:
    """
    Process a list of threads and store new ones to database.
    """
    new_rows = 0

    for th in threads:
        tid = th["id"]
        msg_key = f"gmail-{address}-{tid}"

        # Skip if already present
        if get_message(user_id, msg_key):
            continue

        # Fetch full thread for details
        try:
            full = svc.users().threads().get(
                userId="me", id=tid, format="full"
            ).execute()
        except Exception as e:
            print(f"[gmail] failed to fetch thread {tid}: {e}")
            continue
            
        msg0 = full["messages"][0]
        hdrs = {h["name"]: h["value"] for h in msg0["payload"].get("headers", [])}
        subj = hdrs.get("Subject", "(no subject)")
        sender = hdrs.get("From", "(unknown)")
        
        # Parse date header or fallback to now
        try:
            parsed_date = email.utils.parsedate_to_datetime(hdrs.get("Date", ""))
            date_iso = parsed_date.isoformat()
        except Exception:
            parsed_date = dt.datetime.utcnow()
            date_iso = parsed_date.isoformat()

        # Skip messages older than 60 days
        sixty_days_ago = datetime.now() - timedelta(days=60)
        if parsed_date.replace(tzinfo=None) < sixty_days_ago:
            continue

        # Extract plain and HTML bodies
        plain, html = _mime_parts(msg0["payload"])
        snippet = msg0.get("snippet", plain[:120])

        # Run LLM to get persistent priority with graceful fallback
        priority = "Normal"  # Default priority if LLM fails
        try:
            prompt = SYSTEM_PROMPT + "\n\n### THREAD:\n" + plain
            raw = call(LLMRequest(prompt=prompt))
            priority = "High" if raw.strip().lower().startswith("high") else "Normal"
        except Exception as e:
            print(f"[gmail] LLM priority classification failed for {msg_key}: {e}")
            # Continue with default "Normal" priority

        # Build DynamoDB item
        body = {
            "subject": subj,
            "snippet": snippet,
            "sender": sender,
            "dateISO": date_iso,
            "plain": plain,
            "html": html,
            "priority": priority,
            "account": address,
            # AI summary & checklist fields empty until /nlp/summaries
            "aiSummary": [],
            "aiChecklist": [],
        }

        # Write to database and count
        try:
            put_msg(user_id, msg_key, body)
            new_rows += 1
            print(f"[gmail] Stored message {msg_key} (AI processing will be done on-demand)")
        except Exception as e:
            print(f"[gmail] failed to store message {msg_key}: {e}")

        # Minimal delay to prevent overwhelming APIs during bulk processing
        time.sleep(0.05)  # Small delay for rate limiting
            
    return new_rows
