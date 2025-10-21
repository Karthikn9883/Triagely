#!/usr/bin/env python3
# init_db.py

"""
Database initialization script for Triagely local SQLite setup.

Creates three main tables:
  1. users         → stores user accounts (id, email, password_hash, name)
  2. oauth_tokens  → stores OAuth tokens per user/provider
  3. messages      → caches email/slack messages per user

Run this script once to create the database:
  python init_db.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "triagely.db")


def init_database():
    """
    Create the SQLite database and tables.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Users table - stores local user accounts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            created_at INTEGER NOT NULL
        )
    """)

    # Index for email lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
    """)

    # 2. OAuth tokens table - stores OAuth tokens for Gmail/Slack
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            user_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            token TEXT NOT NULL,
            connected_at INTEGER NOT NULL,
            PRIMARY KEY (user_id, provider)
        )
    """)

    # 3. Messages table - caches email/slack messages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            user_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            subject TEXT,
            snippet TEXT,
            sender TEXT,
            sender_email TEXT,
            date_iso TEXT,
            plain TEXT,
            html TEXT,
            priority TEXT DEFAULT 'Normal',
            account TEXT,
            ai_summary TEXT,
            ai_checklist TEXT,
            created_at INTEGER NOT NULL,
            PRIMARY KEY (user_id, message_id)
        )
    """)

    # Indexes for efficient queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_user_date
        ON messages(user_id, date_iso DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_user_priority
        ON messages(user_id, priority, date_iso DESC)
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database initialized successfully at: {DB_PATH}")


if __name__ == "__main__":
    init_database()
