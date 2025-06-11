import asyncio
import logging
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth import current_user
from app.integrations.gmail.router import router as gmail_router
from app.integrations.slack.router import router as slack_router
from app.background.scheduler       import poll_gmail_forever   # 👈 NEW
from app.nlp import router as nlp_router



# ───────── logging ─────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)s  %(name)s: %(message)s",
)
logger = logging.getLogger("app.main")
logger.info("Logging ready (%s)", LOG_LEVEL)

# ───────── FastAPI app ─────
app = FastAPI()

# CORS so React (localhost:3000) can talk to FastAPI (8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health-checks ---------------------------------------------------
@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/protected")
async def protected_route(user=Depends(current_user)):
    return {"message": f"Hello {user.get('email','?')} (sub: {user.get('sub')})"}

# Routers ---------------------------------------------------------
app.include_router(gmail_router)
app.include_router(slack_router)
app.include_router(nlp_router.router)

# ───────── BACKGROUND POLLER – this was missing ─────────────────
@app.on_event("startup")
async def _launch_poller() -> None:
    """
    Spawn one long-running asyncio-task that keeps every Gmail
    inbox in DynamoDB fresh.  Runs for the life of the process.
    """
    asyncio.create_task(poll_gmail_forever())
    logger.info("📬  Gmail poller task started")