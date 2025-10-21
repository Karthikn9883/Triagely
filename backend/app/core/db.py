# app/core/db.py

"""
Low-level SQLite helpers for Triagely integrations.

Defines three main tables:

  1. users          → stores local user accounts
  2. oauth_tokens   → stores OAuth tokens for each user and provider
  3. messages       → caches email/slack messages per user

Provides functions to save and retrieve tokens, list all Gmail tokens,
and put/query messages with deduplication.
"""
from __future__ import annotations
import os
import time
import json
import sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager

# Database file path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "triagely.db")


@contextmanager
def get_db():
    """
    Context manager for database connections.
    Ensures connections are properly closed.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable dict-like row access
    try:
        yield conn
    finally:
        conn.close()


# ───────────────────────────── User management ──────────────────────────────

def create_user(user_id: str, email: str, password_hash: str, name: str = None) -> None:
    """
    Create a new user account.

    Args:
      user_id: Unique user identifier (UUID).
      email: User's email address (unique).
      password_hash: Hashed password.
      name: Optional user's full name.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (id, email, password_hash, name, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, email, password_hash, name, int(time.time()))
        )
        conn.commit()


def get_user_by_email(email: str) -> dict | None:
    """
    Retrieve a user by email address.

    Args:
      email: User's email address.

    Returns:
      User dict if found, otherwise None.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    """
    Retrieve a user by ID.

    Args:
      user_id: User's unique identifier.

    Returns:
      User dict if found, otherwise None.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


# ───────────────────────────── OAuth tokens ──────────────────────────────

def save_token(uid: str, provider_key: str, token: dict | str) -> None:
    """
    Persist an OAuth token for a given user and provider.

    Args:
      uid: User ID (string) used as partition key.
      provider_key: unique key for service, e.g. 'gmail:alice@example.com' or 'slack'.
      token: OAuth token payload (dict) or raw string; if dict, will be JSON-encoded.

    Effect:
      Inserts or overwrites an item in 'oauth_tokens' with a timestamp.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        token_str = json.dumps(token) if isinstance(token, dict) else token
        cursor.execute(
            """
            INSERT OR REPLACE INTO oauth_tokens (user_id, provider, token, connected_at)
            VALUES (?, ?, ?, ?)
            """,
            (uid, provider_key, token_str, int(time.time()))
        )
        conn.commit()


def get_token(uid: str, provider_key: str) -> dict | None:
    """
    Retrieve a stored OAuth token for a user-provider.

    Args:
      uid: User ID.
      provider_key: provider sort key.

    Returns:
      Decoded token dict if found, otherwise None.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT token FROM oauth_tokens WHERE user_id = ? AND provider = ?",
            (uid, provider_key)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row["token"])
        return None


def list_gmail_tokens(uid: str) -> list[dict]:
    """
    List all Gmail OAuth tokens for a single user.

    Gmail provider_key entries start with 'gmail:'.

    Args:
      uid: User ID.

    Returns:
      List of dicts with keys 'UserID', 'Provider', 'token', etc.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id AS UserID, provider AS Provider, token, connected_at
            FROM oauth_tokens
            WHERE user_id = ? AND provider LIKE 'gmail:%'
            """,
            (uid,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def all_gmail_tokens() -> list[tuple[str, str]]:
    """
    Scan and return every Gmail token entry across all users.

    Returns:
      List of tuples: (user_id, provider) for each Gmail row.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, provider
            FROM oauth_tokens
            WHERE provider LIKE 'gmail:%'
            """
        )
        rows = cursor.fetchall()
        return [(row["user_id"], row["provider"]) for row in rows]


# ───────────────────────────── Messages table ──────────────────────────

def put_msg(uid: str, msg_id: str, body: dict) -> None:
    """
    Insert a message into 'messages' if not already present.

    Args:
      uid: User ID (partition key).
      msg_id: unique message/thread ID for sort key.
      body: dict of message attributes (subject, snippet, etc.).
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if message already exists
        cursor.execute(
            "SELECT 1 FROM messages WHERE user_id = ? AND message_id = ?",
            (uid, msg_id)
        )
        if cursor.fetchone():
            return  # Message already exists, skip insert

        # Convert lists to JSON strings for storage
        ai_summary = json.dumps(body.get("aiSummary", []))
        ai_checklist = json.dumps(body.get("aiChecklist", []))

        cursor.execute(
            """
            INSERT INTO messages (
                user_id, message_id, subject, snippet, sender, sender_email,
                date_iso, plain, html, priority, account, ai_summary, ai_checklist, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uid,
                msg_id,
                body.get("subject"),
                body.get("snippet"),
                body.get("sender"),
                body.get("senderEmail"),
                body.get("dateISO"),
                body.get("plain"),
                body.get("html"),
                body.get("priority", "Normal"),
                body.get("account"),
                ai_summary,
                ai_checklist,
                int(time.time())
            )
        )
        conn.commit()


def update_message_ai(uid: str, msg_id: str, ai_summary: list, ai_checklist: list) -> None:
    """
    Update AI summary and checklist for an existing message.

    Args:
      uid: User ID.
      msg_id: Message ID.
      ai_summary: List of summary bullet points.
      ai_checklist: List of checklist items.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE messages
            SET ai_summary = ?, ai_checklist = ?
            WHERE user_id = ? AND message_id = ?
            """,
            (json.dumps(ai_summary), json.dumps(ai_checklist), uid, msg_id)
        )
        conn.commit()


def get_message(uid: str, msg_id: str) -> dict | None:
    """
    Retrieve a single message by user ID and message ID.

    Args:
      uid: User ID.
      msg_id: Message ID.

    Returns:
      Message dict if found, otherwise None.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM messages WHERE user_id = ? AND message_id = ?",
            (uid, msg_id)
        )
        row = cursor.fetchone()
        if row:
            msg = dict(row)
            # Convert JSON strings back to lists
            msg["MessageID"] = msg.pop("message_id")
            msg["UserID"] = msg.pop("user_id")
            msg["dateISO"] = msg.pop("date_iso")
            msg["senderEmail"] = msg.pop("sender_email")
            msg["aiSummary"] = json.loads(msg.pop("ai_summary") or "[]")
            msg["aiChecklist"] = json.loads(msg.pop("ai_checklist") or "[]")
            msg.pop("created_at", None)
            return msg
        return None


def list_msgs(uid: str, limit: int = 50, page: int = 1, priority_filter: str = None) -> dict:
    """
    Query recent cached messages for a user with pagination support.

    Args:
      uid: User ID.
      limit: maximum number of items to return per page.
      page: page number (1-indexed).
      priority_filter: optional priority filter ('High', 'Normal', None for all).

    Returns:
      Dict with pagination metadata and items: {
        "items": [...],
        "pagination": {
          "current_page": int,
          "total_pages": int,
          "total_count": int,
          "page_size": int
        }
      }
    """
    # Calculate 60 days ago timestamp for filtering
    sixty_days_ago = datetime.now() - timedelta(days=60)
    sixty_days_ago_iso = sixty_days_ago.isoformat()

    with get_db() as conn:
        cursor = conn.cursor()

        # Build query with filters
        query = """
            SELECT * FROM messages
            WHERE user_id = ? AND date_iso >= ?
        """
        params = [uid, sixty_days_ago_iso]

        if priority_filter:
            query += " AND priority = ?"
            params.append(priority_filter)

        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        # Calculate pagination
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
        current_page = max(1, min(page, total_pages)) if total_pages > 0 else 1
        offset = (current_page - 1) * limit

        # Get paginated results
        query += " ORDER BY date_iso DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convert rows to dicts and parse JSON fields
        items = []
        for row in rows:
            msg = dict(row)
            msg["MessageID"] = msg.pop("message_id")
            msg["UserID"] = msg.pop("user_id")
            msg["dateISO"] = msg.pop("date_iso")
            msg["senderEmail"] = msg.pop("sender_email")
            msg["aiSummary"] = json.loads(msg.pop("ai_summary") or "[]")
            msg["aiChecklist"] = json.loads(msg.pop("ai_checklist") or "[]")
            msg.pop("created_at", None)
            items.append(msg)

        return {
            "items": items,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "total_count": total_count,
                "page_size": limit
            }
        }


def cleanup_old_messages() -> int:
    """
    Remove messages older than 60 days from all users.

    Returns:
        Number of messages deleted.
    """
    sixty_days_ago = datetime.now() - timedelta(days=60)
    sixty_days_ago_iso = sixty_days_ago.isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM messages WHERE date_iso < ?",
            (sixty_days_ago_iso,)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count


def cleanup_old_messages_for_user(user_id: str) -> int:
    """
    Remove messages older than 60 days for a specific user.

    Args:
        user_id: User ID.

    Returns:
        Number of messages deleted.
    """
    sixty_days_ago = datetime.now() - timedelta(days=60)
    sixty_days_ago_iso = sixty_days_ago.isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM messages WHERE user_id = ? AND date_iso < ?",
            (user_id, sixty_days_ago_iso)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count
