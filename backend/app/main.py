# app/main.py

import asyncio             # For background tasks
import logging             # Python logging framework
import os                  # Environment variable access
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Import the auth dependency to protect certain endpoints
from app.core.auth import current_user

# Bring in routers from each integration module
from app.integrations.gmail.router import router as gmail_router
from app.integrations.slack.router import router as slack_router

# Background scheduler that polls Gmail periodically to keep cache fresh
from app.background.scheduler import poll_gmail_forever

# NLP router grouping summary/checklist/priority endpoints
from app.nlp import router as nlp_router


# ────────────────────
# 1) Logging configuration
# ────────────────────
# Read desired log level from environment or default to INFO
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s  %(levelname)s  %(name)s: %(message)s",
)
logger = logging.getLogger("app.main")
logger.info("Logging ready (%s)", LOG_LEVEL)


# ────────────────────
# 2) Initialize FastAPI application
# ────────────────────
app = FastAPI(
    title="Triagely API",
    description="Backend for Triagely: unified inbox with AI summaries and priorities",
    version="1.0.0",
)

# Allow Cross-Origin requests from our React front-end
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────
# 3) Health and protected endpoints
# ────────────────────
@app.get("/health")
async def health():
    """
    Public health-check endpoint. Returns OK if service is running.
    """
    return {"ok": True}

@app.get("/protected")
async def protected_route(user=Depends(current_user)):
    """
    Example protected route demonstrating Cognito JWT auth.
    `current_user` will raise 401 if token is invalid.
    """
    return {"message": f"Hello {user.get('email','?')} (sub: {user.get('sub')})"}


# ────────────────────
# 4) Include feature routers
# ────────────────────
# Mount Gmail OAuth, callback, fetch, list endpoints under /gmail
app.include_router(gmail_router)
# Mount Slack OAuth endpoints under /slack
app.include_router(slack_router)
# Mount NLP endpoints (summaries, checklists, priority) under /nlp
app.include_router(nlp_router.router)


# ────────────────────
# 5) Background Gmail poller
# ────────────────────
@app.on_event("startup")
async def _launch_poller() -> None:
    """
    On application startup, spawn a background task that:
    1) Waits 5s to ensure DB connections are ready
    2) Polls every Gmail account in DynamoDB every 2 minutes
    3) Fetches unseen threads and stores them in cache (DynamoDB)
    """
    # Launch as a fire-and-forget asyncio task
    asyncio.create_task(poll_gmail_forever())
    logger.info("📬  Gmail poller task started")
