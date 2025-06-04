# Background poller that keeps the cache warm.
# Called once on startup by FastAPI (see app.main).

import asyncio, logging
from app.core.db import all_gmail_tokens
from app.integrations.gmail import service

log       = logging.getLogger("gmail.poller")
POLL_SEC  = 120            # every two minutes


async def poll_gmail_forever() -> None:
    """Continuously sync every Gmail account in the database."""
    await asyncio.sleep(5)     # give FastAPI a moment to start
    while True:
        for uid, _prov in all_gmail_tokens():       # _prov not needed any more
            try:
                new_ = service.fetch_for_user(uid, max_threads=30)
                if new_:
                    log.info("%s new threads added for %s", len(new_), uid)
            except Exception as exc:
                log.warning("Poll failed for %s: %s", uid, exc)
        await asyncio.sleep(POLL_SEC)