import logging
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.auth import current_user
from app.integrations.gmail.router import router as gmail_router
from app.integrations.slack.router import router as slack_router

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Ensures logs go to console (stderr by default)
    ]
)

# Optional: Add a line to confirm logging is configured
logger = logging.getLogger(__name__)
logger.info("Logging configured at level %s", LOG_LEVEL)

# Initialize FastAPI app
app = FastAPI()

# ⛔️ CORS so React (localhost:3000) can talk to FastAPI (8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/protected")
async def protected_route(user=Depends(current_user)):
    return {
        "message": f"Hello, {user.get('email', 'unknown')} (sub: {user.get('sub')})"
    }

# mount our two integration routers
app.include_router(gmail_router)
app.include_router(slack_router)
