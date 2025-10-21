# app/background/scheduler.py

"""
Background scheduler that periodically polls Gmail accounts to keep
Triagely's DynamoDB cache up-to-date with the latest email threads.

This module is invoked once at FastAPI startup (see app/main.py),
spawning a long-running asyncio task that:
  1) Waits briefly for the server to initialize
  2) Iterates over every stored Gmail OAuth token
  3) Calls the Gmail service layer to fetch new threads
  4) Logs any new threads or warnings on failure
  5) Sleeps for a fixed interval before repeating
"""
import asyncio
import logging
from datetime import datetime, timedelta

from app.core.db import all_gmail_tokens, cleanup_old_messages
from app.integrations.gmail import service

# Logger namespace for scheduler events
log = logging.getLogger("gmail.poller")

# Polling interval in seconds: every 5 minutes (reduced frequency to minimize API usage)
POLL_SEC = 300

# Track last cleanup time
last_cleanup_date = None


async def poll_gmail_forever() -> None:
    """
    Continuously sync every Gmail inbox registered in DynamoDB.

    Lifecycle:
      1. Initial delay of 5s to allow FastAPI startup.
      2. Infinite loop:
         a) For each (userID, provider) tuple from all_gmail_tokens():
            - Call service.fetch_for_user(userID) to insert new threads.
            - If new threads were added, log the count.
            - Catch and warn on any individual polling errors.
         b) Sleep for POLL_SEC seconds before next iteration.

    Important:
      • This task runs in the background for the lifetime of the FastAPI
        process (spawned in app/main.py @startup).
      • Using a single long-lived asyncio task avoids blocking the
        main event loop with synchronous scans.
      • Failure in one account's poll does not abort the overall loop.
    """
    # Initial startup delay to ensure DB connections and routers are ready
    await asyncio.sleep(5)

    # Endless polling loop
    while True:
        # Check if we need to run daily cleanup
        await _run_daily_cleanup()
        
        # Retrieve all Gmail tokens: list of (userID, provider_key)
        for uid, _prov in all_gmail_tokens():
            try:
                # Fetch up to 20 threads per account (reduced from 30 to minimize API usage)
                new_count = service.fetch_for_user(uid, max_threads=20)
                if new_count:
                    # Log how many new threads were added for this user
                    log.info("%s new threads added for %s", new_count, uid)
            except Exception as exc:
                # Log and continue if a poll for a single user fails
                log.warning("Poll failed for %s: %s", uid, exc)

        # Wait POLL_SEC seconds before next full sweep
        await asyncio.sleep(POLL_SEC)


async def _run_daily_cleanup() -> None:
    """
    Run cleanup of old messages once per day.
    """
    global last_cleanup_date
    current_date = datetime.now().date()
    
    # Run cleanup if we haven't run it today
    if last_cleanup_date != current_date:
        try:
            log.info("Starting daily cleanup of messages older than 90 days")
            deleted_count = cleanup_old_messages()
            log.info("Daily cleanup completed: %s messages deleted", deleted_count)
            last_cleanup_date = current_date
        except Exception as exc:
            log.error("Daily cleanup failed: %s", exc)
